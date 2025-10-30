import os
import argparse
import requests
import json
from bs4 import BeautifulSoup
from pyspark.sql import SparkSession
from pyspark.sql.functions import broadcast, col, lower, regexp_replace, udf
from pyspark.sql.types import BooleanType, StringType

def create_spark_session(app_name: str = "URLViolationDetector", master: str | None = None) -> SparkSession:
    """Creates and returns a Spark session.

    When running in cluster, pass master via args or env; defaults to local[*].
    """
    builder = SparkSession.builder.appName(app_name)
    builder = builder.master(master or os.environ.get("SPARK_MASTER", "local[*]"))
    
    # Comprehensive Java 21 compatibility configuration
    java_options = (
        "--add-opens=java.base/java.lang=ALL-UNNAMED "
        "--add-opens=java.base/java.lang.invoke=ALL-UNNAMED "
        "--add-opens=java.base/java.lang.reflect=ALL-UNNAMED "
        "--add-opens=java.base/java.io=ALL-UNNAMED "
        "--add-opens=java.base/java.net=ALL-UNNAMED "
        "--add-opens=java.base/java.nio=ALL-UNNAMED "
        "--add-opens=java.base/java.util=ALL-UNNAMED "
        "--add-opens=java.base/java.util.concurrent=ALL-UNNAMED "
        "--add-opens=java.base/java.util.concurrent.atomic=ALL-UNNAMED "
        "--add-opens=java.base/sun.nio.ch=ALL-UNNAMED "
        "--add-opens=java.base/sun.nio.cs=ALL-UNNAMED "
        "--add-opens=java.base/sun.security.action=ALL-UNNAMED "
        "--add-opens=java.base/sun.util.calendar=ALL-UNNAMED "
        "--add-opens=java.security.jgss/sun.security.krb5=ALL-UNNAMED "
        "--add-opens=java.base/sun.security.util=ALL-UNNAMED "
        "--add-opens=java.base/sun.security.x509=ALL-UNNAMED "
        "--add-opens=java.base/sun.security.provider=ALL-UNNAMED "
        "--add-opens=java.base/sun.security.pkcs=ALL-UNNAMED "
        "--add-opens=java.base/sun.security.ssl=ALL-UNNAMED "
        "--add-opens=java.base/sun.security.timestamp=ALL-UNNAMED "
        "--add-opens=java.base/sun.security.tools.keytool=ALL-UNNAMED "
        "--add-opens=java.base/sun.security.validator=ALL-UNNAMED "
        "--enable-native-access=ALL-UNNAMED "
        "-Djdk.reflect.useDirectMethodHandle=false "
        "-Dio.netty.tryReflectionSetAccessible=true "
        "-Dio.netty.util.internal.logging.InternalLoggerFactory=io.netty.util.internal.logging.JdkLoggerFactory "
        "-Dlog4j2.configurationFile=log4j2.properties"
    )
    
    # Additional Spark configurations for Java 21
    builder = builder.config("spark.driver.extraJavaOptions", java_options)
    builder = builder.config("spark.executor.extraJavaOptions", java_options)
    builder = builder.config("spark.sql.adaptive.enabled", "true")
    builder = builder.config("spark.sql.adaptive.coalescePartitions.enabled", "true")
    builder = builder.config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
    builder = builder.config("spark.sql.execution.arrow.pyspark.enabled", "false")
    builder = builder.config("spark.sql.execution.arrow.maxRecordsPerBatch", "0")
    builder = builder.config("spark.driver.memory", "2g")
    builder = builder.config("spark.executor.memory", "2g")
    builder = builder.config("spark.driver.maxResultSize", "1g")
    
    return builder.getOrCreate()


OLLAMA_URL = "http://host.docker.internal:11434/api/generate"
OLLAMA_MODEL = "gemma"

def analyze_content(url: str, keywords: list) -> bool:
    """
    Fetches URL content, analyzes it with Ollama, and returns True if it's a violation.
    This function is designed to be used as a Spark UDF.
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}
        response = requests.get(url, timeout=15, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        text = ' '.join(t.strip() for t in soup.stripped_strings)

        if not text:
            return False

        candidate_labels = ["an toàn", "tin giả", "kích động", "lừa đảo", "tiêu cực"] + keywords
        prompt = f"""
        Phân tích văn bản sau và phân loại nó vào một trong các nhãn sau: {', '.join(candidate_labels)}.
        Văn bản: --- {text} ---
        Chỉ trả về một JSON object với key "label". Ví dụ: {{"label": "tin giả"}}
        """

        payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False, "format": "json"}
        ollama_response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        ollama_response.raise_for_status()

        model_output = json.loads(ollama_response.json().get("response", "{}"))
        label = model_output.get("label", "an toàn")

        risky_labels = ["tin giả", "kích động", "lừa đảo", "tiêu cực"] + keywords
        return label in risky_labels
    except Exception:
        # If any error occurs (network, parsing, etc.), treat it as non-violating.
        return False

def main():
    """
    Main function to process URLs, detect violations using a broadcast join, and save the results.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    parser = argparse.ArgumentParser(description="Detect violated URLs using Spark")
    parser.add_argument("--urls", dest="urls_csv_path", default=os.path.join(project_root, 'data', 'urls.csv'), help="Path to input CSV with column 'url'")
    parser.add_argument("--keywords", dest="keywords_txt_path", default=os.path.join(project_root, 'data', 'keywords_violation.txt'), help="Path to violation keywords .txt")
    parser.add_argument("--output", dest="output_dir", default=os.path.join(script_dir, 'violated_urls.csv'), help="Output directory to write CSV result")
    parser.add_argument("--master", dest="master", default=None, help="Spark master, e.g. local[*] or spark://host:7077")
    parser.add_argument("--method", dest="method", default="url_only", choices=["url_only", "ollama_content"], help="The analysis method to use.")
    args = parser.parse_args()

    urls_csv_path = args.urls_csv_path
    keywords_txt_path = args.keywords_txt_path
    output_csv_path = args.output_dir

    print(f"[Spark] Input URLs: {urls_csv_path}")
    print(f"[Spark] Keywords: {keywords_txt_path}")
    print(f"[Spark] Output dir: {output_csv_path}")

    spark = create_spark_session(master=args.master)

    # Load keywords into a DataFrame
    try:
        keywords_df = spark.read.text(keywords_txt_path).toDF("keyword")
        keywords_df = keywords_df.filter(~col("keyword").startswith("#") & (col("keyword") != ""))\
                                 .select(lower(col("keyword")).alias("keyword"))

        if keywords_df.count() == 0:
            print(f"Warning: No violation keywords found in '{keywords_txt_path}'. The output will be empty.")
            spark.stop()
            return
    except Exception as e:
        print(f"Error reading keywords file '{keywords_txt_path}': {e}")
        spark.stop()
        return

    # Read the URLs CSV file
    try:
        urls_df = spark.read.option("encoding", "UTF-8").csv(urls_csv_path, header=True, inferSchema=True)
        if "url" not in urls_df.columns:
            print(f"Error: The CSV file at '{urls_csv_path}' must contain a 'url' column.")
            spark.stop()
            return
    except Exception as e:
        print(f"Error reading '{urls_csv_path}': {e}")
        spark.stop()
        return

    # Prepare the URL data by replacing hyphens with spaces and converting to lowercase
    urls_to_check_df = urls_df.withColumn(
        "processed_url",
        lower(regexp_replace(col("url"), "-", " "))
    )

    if args.method == 'url_only':
        print("[Spark] Using URL-only analysis method.")
        # Use a broadcast join with a filter condition to find matches.
        violated_urls_df = urls_to_check_df.join(
            broadcast(keywords_df),
            urls_to_check_df.processed_url.contains(keywords_df.keyword)
        ).select(urls_df["url"], urls_df["date"]).distinct()
    elif args.method == 'ollama_content':
        print("[Spark] Using Ollama content analysis method. This will be very slow.")
        # Collect keywords to pass to the UDF
        keyword_list = [row.keyword for row in keywords_df.collect()]

        # Register the UDF
        analyze_content_udf = udf(lambda url: analyze_content(url, keyword_list), BooleanType())

        # Filter URLs based on the UDF result
        violated_urls_df = urls_df.filter(analyze_content_udf(col("url")))\
                                .select("url", "date")
    else:
        print(f"Error: Unknown method '{args.method}'")
        spark.stop()
        return

    # Save the results
    try:
        violated_urls_df.coalesce(1).write.mode("overwrite").csv(output_csv_path, header=True)
        print(f"Violated URLs have been saved to '{output_csv_path}'")
    except Exception as e:
        print(f"Error saving data to '{output_csv_path}': {e}")
        spark.stop()
        return

    # Show the first 10 results
    print("\n--- First 10 Violated URLs ---")
    violated_urls_df.show(10, truncate=False)

    spark.stop()

if __name__ == "__main__":
    main()
import os
import argparse
from pyspark.sql import SparkSession
from pyspark.sql.functions import broadcast, col, lower, regexp_replace

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

    # Use a broadcast join with a filter condition to find matches.
    violated_urls_df = urls_to_check_df.join(
        broadcast(keywords_df),
        urls_to_check_df.processed_url.contains(keywords_df.keyword)
    )

    # Select columns conditionally based on the presence of a 'date' column
    if "date" in urls_df.columns:
        violated_urls_df = violated_urls_df.select(urls_df["url"], urls_df["date"]).distinct()
    else:
        violated_urls_df = violated_urls_df.select(urls_df["url"]).distinct()

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
from sedona.utils import SedonaKryoRegistrator, KryoSerializer
from pyspark.sql import SparkSession
import os
spark = SparkSession.builder \
    .appName("SedonaVersionCheck") \
    .config("spark.serializer", KryoSerializer.getName) \
    .config("spark.kryo.registrator", SedonaKryoRegistrator.getName) \
    .getOrCreate()
# Get Pod IP (via socket)
# Get Pod Name (K8s exposes it as env var if configured)
pod_name = os.environ.get("JUPYTERHUB_USER", "unknown")

print("Result from worker: ======START======")
print("Apache Sedona version:", spark.version)
print("My mode:", pod_name)
print("Result from worker: ======END======")
spark.stop()

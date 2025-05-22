apk add zip
apk add openjdk11
export JAVA_HOME=$(dirname $(dirname $(readlink -f $(which java))))

pip install apache-sedona -t sedona_deps/
cd sedona_deps && zip -r ../sedona_deps.zip . && cd ..


curl -O https://downloads.apache.org/spark/spark-3.5.5/spark-3.5.5-bin-hadoop3.tgz
tar -xzf spark-3.5.5-bin-hadoop3.tgz
export PATH=$PWD/spark-3.5.5-bin-hadoop3/bin:$PATH

spark-submit \
  --master spark://spark-master-svc.hyperplane-spark.svc.cluster.local:7077 \
  --deploy-mode client \
  --py-files sedona_deps.zip \
  sedona_version.py

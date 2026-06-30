# DolphinScheduler + SeaTunnel 任务编排与数据获取系统设计文档

> **本文档只提供初次部署内容，与线上环境不一致请以线上为准**

***

## 1. 系统概述

### 1.1 系统目标

构建一套基于 **Apache DolphinScheduler**（任务编排调度平台）+ **Apache SeaTunnel**（数据集成引擎）的高可用、可扩展的任务编排与数据获取系统，满足以下核心需求：

- **任务编排**: 可视化 DAG 工作流定义，支持复杂依赖关系、定时调度、依赖触发
- **数据获取**: 支持多种数据源（MySQL、PostgreSQL、Kafka、HDFS、ClickHouse 等）之间的批量/实时数据同步
- **高可用**: 集群化部署，无单点故障，Master/Worker 支持故障自动转移
- **可扩展**: 水平扩展 Worker 节点提升任务处理能力
- **可观测**: 完整的任务监控、日志查看、告警通知能力

### 1.2 技术选型

| 组件     | 选型                      | 版本     | 说明                           |
| ------ | ----------------------- | ------ | ---------------------------- |
| 任务调度引擎 | Apache DolphinScheduler | 3.4.2  | 分布式 DAG 工作流调度                |
| 数据集成引擎 | Apache SeaTunnel        | 2.3.13 | 高性能数据同步（Zeta 引擎分离集群模式）       |
| 元数据库   | MySQL（现有）               | 8.0+   | DS 元数据存储，直接连接现有实例            |
| 注册中心   | ZooKeeper               | 3.8.3  | DS 集群协调、服务发现                 |
| 部署平台   | 华为云 CCE                 | -      | Kubernetes StatefulSet 有状态负载 |
| JDK    | OpenJDK                 | 11     | 运行环境（容器镜像内置）                 |

***

## 2. 系统架构设计

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         华为云 CCE 集群                                       │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  Namespace: dolphinscheduler                                         │   │
│  │                                                                      │   │
│  │  ┌─────────────────────┐  ┌─────────────────────┐                   │   │
│  │  │  ds-master-0        │  │  ds-master-1        │  ← DS Master x2   │   │
│  │  │  (Master+API+Alert) │  │  (Master+API+Alert) │     StatefulSet   │   │
│  │  └─────────┬───────────┘  └─────────┬───────────┘                   │   │
│  │            │                         │                               │   │
│  │  ┌─────────▼─────────────────────────▼───────────┐                   │   │
│  │  │           ZooKeeper 集群                       │  ← ZK x3        │   │
│  │  │  zk-0 ── zk-1 ── zk-2 (StatefulSet)          │     StatefulSet  │   │
│  │  └─────────────────────┬─────────────────────────┘                   │   │
│  │                        │                                             │   │
│  │  ┌─────────────────────▼─────────────────────────┐                   │   │
│  │  │           MySQL（现有，CCE外或RDS）              │  ← 连接现有MySQL  │   │
│  │  └─────────────────────────────────────────────────┘                   │   │
│  │                                                                      │   │
│  │  ┌─────────────────────┐  ┌─────────────────────┐                   │   │
│  │  │  ds-worker-0        │  │  ds-worker-1        │  ← DS Worker x4   │   │
│  │  ├─────────────────────┤  ├─────────────────────┤     StatefulSet   │   │
│  │  │  ds-worker-2        │  │  ds-worker-3        │                   │   │
│  │  └─────────────────────┘  └─────────────────────┘                   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  Namespace: seatunnel                                                │   │
│  │                                                                      │   │
│  │  ┌─────────────────────┐  ┌─────────────────────┐                   │   │
│  │  │  st-master-0        │  │  st-master-1        │  ← ST Master x2   │   │
│  │  │  (Zeta Master)      │  │  (Zeta Master)      │     StatefulSet   │   │
│  │  └─────────────────────┘  └─────────────────────┘                   │   │
│  │                                                                      │   │
│  │  ┌─────────────────────┐  ┌─────────────────────┐                   │   │
│  │  │  st-worker-0        │  │  st-worker-1        │  ← ST Worker x4   │   │
│  │  ├─────────────────────┤  ├─────────────────────┤     StatefulSet   │   │
│  │  │  st-worker-2        │  │  st-worker-3        │                   │   │
│  │  └─────────────────────┘  └─────────────────────┘                   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  数据源 / 目标端                                                      │   │
│  │  MySQL / PG / Kafka / HDFS / ClickHouse / ES                         │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 CCE 资源规划总览

| 有状态负载 (StatefulSet) | 副本数 | 容器规格   | 存储      | 说明                      |
| ------------------- | --- | ------ | ------- | ----------------------- |
| `ds-master`         | 2   | 4C/8G  | 20G 数据盘 | DS Master + API + Alert |
| `ds-worker`         | 4   | 8C/16G | 50G 数据盘 | DS Worker               |
| `zk`                | 3   | 2C/4G  | 20G 数据盘 | ZooKeeper 集群            |
| `st-master`         | 2   | 4C/8G  | 20G 数据盘 | SeaTunnel Zeta Master   |
| `st-worker`         | 4   | 8C/16G | 50G 数据盘 | SeaTunnel Zeta Worker   |

### 2.3 核心组件说明

#### 2.3.1 DolphinScheduler 组件

| 组件               | 职责                     | CCE 部署方式                       |
| ---------------- | ---------------------- | ------------------------------ |
| **MasterServer** | DAG 任务切分、任务提交监控、集群健康管理 | StatefulSet 2 副本，含 API + Alert |
| **WorkerServer** | 实际任务执行、日志服务            | StatefulSet 4 副本，支持标签分组        |
| **API Server**   | RESTful API 接口、前端请求处理  | 与 Master 同 Pod 部署              |
| **Alert Server** | 告警通知（邮件、钉钉、飞书、企业微信等）   | 与 Master 同 Pod 部署              |
| **ZooKeeper**    | 服务注册与发现、分布式锁、领导者选举     | StatefulSet 3 副本               |

#### 2.3.2 SeaTunnel 组件

| 组件                   | 职责                           | CCE 部署方式         |
| -------------------- | ---------------------------- | ---------------- |
| **Zeta Master**      | 任务调度、REST API、元数据管理          | StatefulSet 2 副本 |
| **Zeta Worker**      | 任务执行、数据同步                    | StatefulSet 4 副本 |
| **Source Connector** | 数据源读取（MySQL、Kafka、HDFS 等）    | 内置于 Worker 镜像    |
| **Sink Connector**   | 数据目标写入（ClickHouse、ES、Hive 等） | 内置于 Worker 镜像    |

### 2.4 数据流架构

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
│  数据源       │     │  SeaTunnel 任务   │     │  数据目标      │
│              │     │                  │     │              │
│ MySQL ───────┼────►│ Source →         │────►│ ClickHouse   │
│ PostgreSQL ──┼────►│ Transform →     │────►│ Elasticsearch│
│ Kafka ───────┼────►│ Sink            │────►│ HDFS/Hive    │
│ HDFS ────────┼────►│                  │────►│ MySQL/PG     │
│ API/HTTP ────┼────►│                  │────►│ Kafka        │
└──────────────┘     └──────────────────┘     └──────────────┘
                            │
                     DolphinScheduler 编排调度
                     (定时/依赖/手动触发)
```

***

## 3. CCE 集群部署规划

### 3.1 CCE 集群规格

| 配置项           | 规格                  |
| ------------- | ------------------- |
| 集群类型          | CCE Standard/Turbo  |
| Kubernetes 版本 | 1.25+               |
| 网络模型          | VPC 网络 / 容器隧道网络     |
| 节点规格          | 通用计算增强型 (C6s/C7)    |
| 节点数量          | 4-6 个 Worker 节点     |
| 容器运行时         | Docker / containerd |

### 3.2 命名空间规划

| 命名空间               | 用途                               |
| ------------------ | -------------------------------- |
| `dolphinscheduler` | DS 所有组件（Master/Worker/ZooKeeper） |
| `seatunnel`        | SeaTunnel 所有组件（Master/Worker）    |

### 3.3 存储规划

使用华为云 CCE 的 **云硬盘 EVS** 作为持久化存储，通过 StorageClass 动态创建 PVC：

| 组件        | 存储类型 | 容量   | 挂载路径                         | 说明      |
| --------- | ---- | ---- | ---------------------------- | ------- |
| ZooKeeper | SSD  | 20Gi | `/data/zookeeper`            | 事务日志+快照 |
| DS Master | SSD  | 20Gi | `/opt/dolphinscheduler/logs` | 日志持久化   |
| DS Worker | SSD  | 50Gi | `/opt/dolphinscheduler/logs` | 日志+临时文件 |
| ST Master | SSD  | 20Gi | `/opt/seatunnel/logs`        | 日志持久化   |
| ST Worker | SSD  | 50Gi | `/opt/seatunnel/logs`        | 日志+数据缓存 |

### 3.4 网络规划

| 服务类型              | 用途                     | 说明             |
| ----------------- | ---------------------- | -------------- |
| Headless Service  | ZooKeeper/DS/ST 集群内部通信 | Pod 间直连 DNS 发现 |
| ClusterIP Service | DS API Server 对外暴露     | 供前端 UI 访问      |
| ClusterIP Service | ST Master REST API     | 供 DS 任务提交调用    |

***

## 4. Docker 镜像构建

### 4.1 DolphinScheduler 镜像

```dockerfile
# Dockerfile-dolphinscheduler
FROM openjdk:11-jre-slim

ENV DS_HOME=/opt/dolphinscheduler
ENV TZ=Asia/Shanghai

# 安装依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    netcat \
    procps \
    && rm -rf /var/lib/apt/lists/*

# 下载 DS 二进制包
RUN wget -q https://dlcdn.apache.org/dolphinscheduler/3.4.2/apache-dolphinscheduler-3.4.2-bin.tar.gz \
    && tar -xzf apache-dolphinscheduler-3.4.2-bin.tar.gz -C /opt/ \
    && mv /opt/apache-dolphinscheduler-3.4.2-bin ${DS_HOME} \
    && rm -f apache-dolphinscheduler-3.4.2-bin.tar.gz

# 添加 MySQL JDBC 驱动
RUN wget -q https://repo1.maven.org/maven2/mysql/mysql-connector-java/8.0.33/mysql-connector-java-8.0.33.jar \
    && cp mysql-connector-java-8.0.33.jar ${DS_HOME}/libs/ \
    && rm -f mysql-connector-java-8.0.33.jar

WORKDIR ${DS_HOME}
```

### 4.2 SeaTunnel 镜像

```dockerfile
# Dockerfile-seatunnel
FROM openjdk:11-jre-slim

ENV ST_HOME=/opt/seatunnel
ENV TZ=Asia/Shanghai

# 安装依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    netcat \
    procps \
    && rm -rf /var/lib/apt/lists/*

# 下载 SeaTunnel 二进制包
RUN wget -q https://dlcdn.apache.org/seatunnel/2.3.13/apache-seatunnel-2.3.13-bin.tar.gz \
    && tar -xzf apache-seatunnel-2.3.13-bin.tar.gz -C /opt/ \
    && mv /opt/apache-seatunnel-2.3.13-bin ${ST_HOME} \
    && rm -f apache-seatunnel-2.3.13-bin.tar.gz

# 安装所有连接器
RUN cd ${ST_HOME} && sh bin/install-plugin.sh --connector-version 2.3.13

WORKDIR ${ST_HOME}
```

### 4.3 ZooKeeper 镜像

使用官方镜像 `bitnami/zookeeper:3.8.3` 或 `apache/zookeeper:3.8.3`。

***

## 5. Kubernetes 资源清单

### 5.1 ZooKeeper StatefulSet

#### 5.1.1 ConfigMap

```yaml
# zk-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: zk-config
  namespace: dolphinscheduler
data:
  zoo.cfg: |
    tickTime=2000
    initLimit=10
    syncLimit=5
    dataDir=/data/zookeeper
    clientPort=2181
    maxClientCnxns=60
    autopurge.snapRetainCount=3
    autopurge.purgeInterval=1
    4lw.commands.whitelist=*
  init.sh: |
    #!/bin/bash
    # 根据 Pod 名称自动计算 myid
    ORDINAL=${HOSTNAME##*-}
    echo ${ORDINAL} > /data/zookeeper/myid
    # 生成 server 配置
    for i in $(seq 0 2); do
      echo "server.${i}=zk-${i}.zk-hs.${POD_NAMESPACE}.svc.cluster.local:2888:3888" >> /opt/zookeeper/conf/zoo.cfg
    done
```

#### 5.1.2 Headless Service

```yaml
# zk-headless-svc.yaml
apiVersion: v1
kind: Service
metadata:
  name: zk-hs
  namespace: dolphinscheduler
spec:
  clusterIP: None
  selector:
    app: zk
  ports:
    - port: 2181
      name: client
    - port: 2888
      name: peer
    - port: 3888
      name: leader-election
```

#### 5.1.3 Client Service

```yaml
# zk-client-svc.yaml
apiVersion: v1
kind: Service
metadata:
  name: zk-cs
  namespace: dolphinscheduler
spec:
  selector:
    app: zk
  ports:
    - port: 2181
      targetPort: 2181
```

#### 5.1.4 StatefulSet

```yaml
# zk-statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: zk
  namespace: dolphinscheduler
spec:
  serviceName: zk-hs
  replicas: 3
  podManagementPolicy: OrderedReady
  selector:
    matchLabels:
      app: zk
  template:
    metadata:
      labels:
        app: zk
    spec:
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchLabels:
                    app: zk
                topologyKey: kubernetes.io/hostname
      containers:
        - name: zookeeper
          image: bitnami/zookeeper:3.8.3
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: 2181
              name: client
            - containerPort: 2888
              name: peer
            - containerPort: 3888
              name: leader-election
          env:
            - name: ZOO_MY_ID
              valueFrom:
                fieldRef:
                  fieldPath: metadata.labels['statefulset.kubernetes.io/pod-name']
            - name: ZOO_SERVERS
              value: "server.1=zk-0.zk-hs.dolphinscheduler.svc.cluster.local:2888:3888;server.2=zk-1.zk-hs.dolphinscheduler.svc.cluster.local:2888:3888;server.3=zk-2.zk-hs.dolphinscheduler.svc.cluster.local:2888:3888"
            - name: ALLOW_ANONYMOUS_LOGIN
              value: "yes"
          resources:
            requests:
              cpu: "1"
              memory: "2Gi"
            limits:
              cpu: "2"
              memory: "4Gi"
          livenessProbe:
            exec:
              command: ["zkServer.sh", "status"]
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            exec:
              command: ["zkServer.sh", "status"]
            initialDelaySeconds: 30
            periodSeconds: 10
          volumeMounts:
            - name: data
              mountPath: /bitnami/zookeeper
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 20Gi
        storageClassName: csi-disk-sas
```

### 5.2 DolphinScheduler Master StatefulSet

#### 5.2.1 ConfigMap

```yaml
# ds-master-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ds-master-config
  namespace: dolphinscheduler
data:
  dolphinscheduler_env.sh: |
    export JAVA_HOME=/usr/local/openjdk-11
    export DATABASE=mysql
    export SPRING_DATASOURCE_URL="jdbc:mysql://mysql-host:3306/dolphinscheduler?useUnicode=true&characterEncoding=UTF-8&useSSL=false&serverTimezone=Asia/Shanghai"
    export SPRING_DATASOURCE_USERNAME="ds_user"
    export SPRING_DATASOURCE_PASSWORD="DolphinScheduler@2026!"
    export REGISTRY_TYPE=zookeeper
    export REGISTRY_ZOOKEEPER_CONNECT_STRING="zk-cs.dolphinscheduler.svc.cluster.local:2181"
    export RESOURCE_STORAGE_TYPE=NONE
    export MAIL_SERVER_HOST=smtp.example.com
    export MAIL_SERVER_PORT=465
    export MAIL_SENDER=alert@example.com
    export MAIL_USER=alert@example.com
    export MAIL_PASSWD=your-password

  master.properties: |
    master.exec.threads=16
    master.host.select.strategy=CPU_LOAD
    master.task.commit.retryTimes=3
    master.workflow.commit.retryTimes=5
    master.statewheel.interval=5000

  application.yaml: |
    server:
      port: 12345
    spring:
      datasource:
        driver-class-name: com.mysql.cj.jdbc.Driver
        url: jdbc:mysql://mysql-host:3306/dolphinscheduler?useUnicode=true&characterEncoding=UTF-8&useSSL=false&serverTimezone=Asia/Shanghai
        username: ds_user
        password: DolphinScheduler@2026!
```

#### 5.2.2 Headless Service

```yaml
# ds-master-hs.yaml
apiVersion: v1
kind: Service
metadata:
  name: ds-master-hs
  namespace: dolphinscheduler
spec:
  clusterIP: None
  selector:
    app: ds-master
  ports:
    - port: 5678
      name: master
```

#### 5.2.3 API Service (对外暴露)

```yaml
# ds-api-svc.yaml
apiVersion: v1
kind: Service
metadata:
  name: ds-api
  namespace: dolphinscheduler
spec:
  type: ClusterIP
  selector:
    app: ds-master
  ports:
    - port: 12345
      targetPort: 12345
      name: api
```

#### 5.2.4 StatefulSet

```yaml
# ds-master-statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: ds-master
  namespace: dolphinscheduler
spec:
  serviceName: ds-master-hs
  replicas: 2
  selector:
    matchLabels:
      app: ds-master
  template:
    metadata:
      labels:
        app: ds-master
    spec:
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchLabels:
                    app: ds-master
                topologyKey: kubernetes.io/hostname
      initContainers:
        - name: init-db
          image: your-registry/dolphinscheduler:3.4.2
          imagePullPolicy: IfNotPresent
          command:
            - /bin/bash
            - -c
            - |
              /opt/dolphinscheduler/tools/bin/upgrade-schema.sh
          env:
            - name: DATABASE
              value: mysql
            - name: SPRING_DATASOURCE_URL
              value: "jdbc:mysql://mysql-host:3306/dolphinscheduler?useUnicode=true&characterEncoding=UTF-8&useSSL=false&serverTimezone=Asia/Shanghai"
            - name: SPRING_DATASOURCE_USERNAME
              value: "ds_user"
            - name: SPRING_DATASOURCE_PASSWORD
              value: "DolphinScheduler@2026!"
      containers:
        - name: master-server
          image: your-registry/dolphinscheduler:3.4.2
          imagePullPolicy: IfNotPresent
          command: ["/bin/bash", "-c"]
          args:
            - |
              source /opt/dolphinscheduler/bin/env/dolphinscheduler_env.sh
              /opt/dolphinscheduler/bin/dolphinscheduler-daemon.sh start master-server
              tail -f /opt/dolphinscheduler/logs/master-server/dolphinscheduler-master.log
          ports:
            - containerPort: 5678
              name: master
            - containerPort: 12345
              name: api
          env:
            - name: TZ
              value: Asia/Shanghai
          resources:
            requests:
              cpu: "2"
              memory: "4Gi"
            limits:
              cpu: "4"
              memory: "8Gi"
          livenessProbe:
            tcpSocket:
              port: 5678
            initialDelaySeconds: 60
            periodSeconds: 15
          readinessProbe:
            tcpSocket:
              port: 12345
            initialDelaySeconds: 30
            periodSeconds: 10
          volumeMounts:
            - name: config
              mountPath: /opt/dolphinscheduler/bin/env/dolphinscheduler_env.sh
              subPath: dolphinscheduler_env.sh
            - name: config
              mountPath: /opt/dolphinscheduler/master-server/conf/master.properties
              subPath: master.properties
            - name: logs
              mountPath: /opt/dolphinscheduler/logs
      volumes:
        - name: config
          configMap:
            name: ds-master-config
  volumeClaimTemplates:
    - metadata:
        name: logs
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 20Gi
        storageClassName: csi-disk-sas
```

### 5.3 DolphinScheduler Worker StatefulSet

#### 5.3.1 ConfigMap

```yaml
# ds-worker-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ds-worker-config
  namespace: dolphinscheduler
data:
  dolphinscheduler_env.sh: |
    export JAVA_HOME=/usr/local/openjdk-11
    export DATABASE=mysql
    export SPRING_DATASOURCE_URL="jdbc:mysql://mysql-host:3306/dolphinscheduler?useUnicode=true&characterEncoding=UTF-8&useSSL=false&serverTimezone=Asia/Shanghai"
    export SPRING_DATASOURCE_USERNAME="ds_user"
    export SPRING_DATASOURCE_PASSWORD="DolphinScheduler@2026!"
    export REGISTRY_TYPE=zookeeper
    export REGISTRY_ZOOKEEPER_CONNECT_STRING="zk-cs.dolphinscheduler.svc.cluster.local:2181"
    export SEATUNNEL_HOME=/opt/seatunnel

  worker.properties: |
    worker.exec.threads=32
    worker.max.cpuload.avg=80
    worker.reserved.memory=2048
    worker.task.dir=/tmp/dolphinscheduler/exec
```

#### 5.3.2 StatefulSet

```yaml
# ds-worker-statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: ds-worker
  namespace: dolphinscheduler
spec:
  serviceName: ds-worker-hs
  replicas: 4
  selector:
    matchLabels:
      app: ds-worker
  template:
    metadata:
      labels:
        app: ds-worker
    spec:
      containers:
        - name: worker-server
          image: your-registry/dolphinscheduler:3.4.2
          imagePullPolicy: IfNotPresent
          command: ["/bin/bash", "-c"]
          args:
            - |
              source /opt/dolphinscheduler/bin/env/dolphinscheduler_env.sh
              /opt/dolphinscheduler/bin/dolphinscheduler-daemon.sh start worker-server
              tail -f /opt/dolphinscheduler/logs/worker-server/dolphinscheduler-worker.log
          ports:
            - containerPort: 1234
              name: worker
          env:
            - name: TZ
              value: Asia/Shanghai
          resources:
            requests:
              cpu: "4"
              memory: "8Gi"
            limits:
              cpu: "8"
              memory: "16Gi"
          livenessProbe:
            tcpSocket:
              port: 1234
            initialDelaySeconds: 60
            periodSeconds: 15
          readinessProbe:
            tcpSocket:
              port: 1234
            initialDelaySeconds: 30
            periodSeconds: 10
          volumeMounts:
            - name: config
              mountPath: /opt/dolphinscheduler/bin/env/dolphinscheduler_env.sh
              subPath: dolphinscheduler_env.sh
            - name: config
              mountPath: /opt/dolphinscheduler/worker-server/conf/worker.properties
              subPath: worker.properties
            - name: logs
              mountPath: /opt/dolphinscheduler/logs
      volumes:
        - name: config
          configMap:
            name: ds-worker-config
  volumeClaimTemplates:
    - metadata:
        name: logs
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 50Gi
        storageClassName: csi-disk-sas
```

### 5.4 SeaTunnel Master StatefulSet

#### 5.4.1 ConfigMap

```yaml
# st-master-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: st-master-config
  namespace: seatunnel
data:
  hazelcast-master.yaml: |
    hazelcast:
      cluster-name: seatunnel-cluster
      network:
        rest-api:
          enabled: true
          endpoint-groups:
            CLUSTER_WRITE:
              enabled: true
            DATA:
              enabled: true
        join:
          kubernetes:
            enabled: true
            service-dns: st-hs.seatunnel.svc.cluster.local
            service-port: 5801
        port:
          auto-increment: false
          port: 5801
      properties:
        hazelcast.invocation.max.retry.count: 20
        hazelcast.tcp.join.port.try.count: 30
        hazelcast.logging.type: log4j2
        hazelcast.operation.generic.thread.count: 50

  seatunnel.yaml: |
    seatunnel:
      engine:
        type: zeta
        backup-count: 1
        queue-type: blockingqueue
        print-execution-info-interval: 60
        slot-service:
          dynamic-slot: true
        checkpoint:
          interval: 60000
          timeout: 600000
          max-concurrent: 5
          tolerable-failure: 2
          storage:
            type: hdfs
            max-retained: 3
            plugin-config:
              namespace: /seatunnel/checkpoint
              storage-type: hdfs
              fs.defaultFS: hdfs://nameservice1:8020
```

#### 5.4.2 Headless Service

```yaml
# st-hs.yaml
apiVersion: v1
kind: Service
metadata:
  name: st-hs
  namespace: seatunnel
spec:
  clusterIP: None
  selector:
    app: st-master
  ports:
    - port: 5801
      name: hazelcast
```

#### 5.4.3 Master REST API Service

```yaml
# st-master-svc.yaml
apiVersion: v1
kind: Service
metadata:
  name: st-master-svc
  namespace: seatunnel
spec:
  type: ClusterIP
  selector:
    app: st-master
  ports:
    - port: 8080
      targetPort: 8080
      name: rest-api
```

#### 5.4.4 StatefulSet

```yaml
# st-master-statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: st-master
  namespace: seatunnel
spec:
  serviceName: st-hs
  replicas: 2
  selector:
    matchLabels:
      app: st-master
  template:
    metadata:
      labels:
        app: st-master
    spec:
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchLabels:
                    app: st-master
                topologyKey: kubernetes.io/hostname
      containers:
        - name: seatunnel-master
          image: your-registry/seatunnel:2.3.13
          imagePullPolicy: IfNotPresent
          command:
            - /bin/bash
            - -c
            - |
              /opt/seatunnel/bin/seatunnel-cluster.sh master -DJvmOption="-Xms4g -Xmx4g -XX:+UseG1GC"
          ports:
            - containerPort: 5801
              name: hazelcast
            - containerPort: 8080
              name: rest-api
          env:
            - name: TZ
              value: Asia/Shanghai
          resources:
            requests:
              cpu: "2"
              memory: "4Gi"
            limits:
              cpu: "4"
              memory: "8Gi"
          livenessProbe:
            tcpSocket:
              port: 5801
            initialDelaySeconds: 60
            periodSeconds: 15
          readinessProbe:
            tcpSocket:
              port: 8080
            initialDelaySeconds: 30
            periodSeconds: 10
          volumeMounts:
            - name: config
              mountPath: /opt/seatunnel/config/hazelcast-master.yaml
              subPath: hazelcast-master.yaml
            - name: config
              mountPath: /opt/seatunnel/config/seatunnel.yaml
              subPath: seatunnel.yaml
            - name: logs
              mountPath: /opt/seatunnel/logs
      volumes:
        - name: config
          configMap:
            name: st-master-config
  volumeClaimTemplates:
    - metadata:
        name: logs
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 20Gi
        storageClassName: csi-disk-sas
```

### 5.5 SeaTunnel Worker StatefulSet

#### 5.5.1 ConfigMap

```yaml
# st-worker-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: st-worker-config
  namespace: seatunnel
data:
  hazelcast-worker.yaml: |
    hazelcast:
      cluster-name: seatunnel-cluster
      network:
        join:
          kubernetes:
            enabled: true
            service-dns: st-hs.seatunnel.svc.cluster.local
            service-port: 5801
        port:
          auto-increment: false
          port: 5801
      properties:
        hazelcast.invocation.max.retry.count: 20
        hazelcast.tcp.join.port.try.count: 30
        hazelcast.logging.type: log4j2
```

#### 5.5.2 StatefulSet

```yaml
# st-worker-statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: st-worker
  namespace: seatunnel
spec:
  serviceName: st-hs
  replicas: 4
  selector:
    matchLabels:
      app: st-worker
  template:
    metadata:
      labels:
        app: st-worker
    spec:
      containers:
        - name: seatunnel-worker
          image: your-registry/seatunnel:2.3.13
          imagePullPolicy: IfNotPresent
          command:
            - /bin/bash
            - -c
            - |
              /opt/seatunnel/bin/seatunnel-cluster.sh worker -DJvmOption="-Xms8g -Xmx8g -XX:+UseG1GC"
          ports:
            - containerPort: 5801
              name: hazelcast
          env:
            - name: TZ
              value: Asia/Shanghai
          resources:
            requests:
              cpu: "4"
              memory: "8Gi"
            limits:
              cpu: "8"
              memory: "16Gi"
          livenessProbe:
            tcpSocket:
              port: 5801
            initialDelaySeconds: 60
            periodSeconds: 15
          readinessProbe:
            tcpSocket:
              port: 5801
            initialDelaySeconds: 30
            periodSeconds: 10
          volumeMounts:
            - name: config
              mountPath: /opt/seatunnel/config/hazelcast-worker.yaml
              subPath: hazelcast-worker.yaml
            - name: logs
              mountPath: /opt/seatunnel/logs
      volumes:
        - name: config
          configMap:
            name: st-worker-config
  volumeClaimTemplates:
    - metadata:
        name: logs
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 50Gi
        storageClassName: csi-disk-sas
```

***

## 6. 部署流程

### 6.1 前提条件

1. 华为云 CCE 集群已创建并可用
2. `kubectl` 已配置连接到 CCE 集群
3. 现有 MySQL 实例可访问，已创建 `dolphinscheduler` 数据库
4. 容器镜像仓库（SWR）已准备就绪

### 6.2 构建并推送镜像

```bash
# 登录华为云 SWR
docker login -u cn-north-4@AK -p SK swr.cn-north-4.myhuaweicloud.com

# 构建 DS 镜像
docker build -f Dockerfile-dolphinscheduler -t swr.cn-north-4.myhuaweicloud.com/your-ns/dolphinscheduler:3.4.2 .
docker push swr.cn-north-4.myhuaweicloud.com/your-ns/dolphinscheduler:3.4.2

# 构建 ST 镜像
docker build -f Dockerfile-seatunnel -t swr.cn-north-4.myhuaweicloud.com/your-ns/seatunnel:2.3.13 .
docker push swr.cn-north-4.myhuaweicloud.com/your-ns/seatunnel:2.3.13
```

### 6.3 创建命名空间

```bash
kubectl create namespace dolphinscheduler
kubectl create namespace seatunnel
```

### 6.4 部署 ZooKeeper

```bash
kubectl apply -f zk-configmap.yaml
kubectl apply -f zk-headless-svc.yaml
kubectl apply -f zk-client-svc.yaml
kubectl apply -f zk-statefulset.yaml

# 验证
kubectl -n dolphinscheduler get pods -l app=zk
kubectl -n dolphinscheduler exec zk-0 -- zkServer.sh status
```

### 6.5 初始化 DS 数据库

```bash
# 连接到现有 MySQL，执行初始化
mysql -h mysql-host -u ds_user -p dolphinscheduler < /opt/dolphinscheduler/sql/dolphinscheduler_mysql.sql
```

### 6.6 部署 DolphinScheduler

```bash
# 部署 Master
kubectl apply -f ds-master-configmap.yaml
kubectl apply -f ds-master-hs.yaml
kubectl apply -f ds-api-svc.yaml
kubectl apply -f ds-master-statefulset.yaml

# 部署 Worker
kubectl apply -f ds-worker-configmap.yaml
kubectl apply -f ds-worker-statefulset.yaml

# 验证
kubectl -n dolphinscheduler get pods -l app=ds-master
kubectl -n dolphinscheduler get pods -l app=ds-worker
```

### 6.7 部署 SeaTunnel

```bash
# 部署 Master
kubectl apply -f st-master-configmap.yaml
kubectl apply -f st-hs.yaml
kubectl apply -f st-master-svc.yaml
kubectl apply -f st-master-statefulset.yaml

# 部署 Worker
kubectl apply -f st-worker-configmap.yaml
kubectl apply -f st-worker-statefulset.yaml

# 验证
kubectl -n seatunnel get pods -l app=st-master
kubectl -n seatunnel get pods -l app=st-worker
```

### 6.8 配置 DS 访问 SeaTunnel

在 DS Web UI 中配置 SeaTunnel 环境：

1. 通过 `ds-api` Service 访问 DS Web UI（端口 12345）
2. 进入 **安全中心 > 环境管理**
3. 创建环境：
   - **环境名称**: `SEATUNNEL_ENV`
   - **环境配置**:
     ```bash
     export SEATUNNEL_HOME=/opt/seatunnel
     export PATH=$SEATUNNEL_HOME/bin:$PATH
     ```
4. 在 **Worker 分组** 中关联该环境

***

## 7. 系统配置优化

### 7.1 DolphinScheduler 配置优化

#### 7.1.1 Master 配置

```properties
# master.exec.threads: 建议 CPU 核心数 * 2-4
master.exec.threads=16
master.host.select.strategy=CPU_LOAD
master.task.commit.retryTimes=3
master.workflow.commit.retryTimes=5
master.statewheel.interval=5000
```

#### 7.1.2 Worker 配置

```properties
worker.exec.threads=32
worker.max.cpuload.avg=80
worker.reserved.memory=2048
worker.task.dir=/tmp/dolphinscheduler/exec
```

### 7.2 SeaTunnel 配置优化

```yaml
# JVM 参数
# Master: -Xms4g -Xmx4g
# Worker: -Xms8g -Xmx8g

# 任务并行度配置
env {
  parallelism = 4
  job.mode = "BATCH"
  checkpoint.interval = 60000
}
```

### 7.3 ZooKeeper 优化

```properties
# zoo.cfg 关键参数
tickTime=2000
initLimit=10
syncLimit=5
maxClientCnxns=100
autopurge.snapRetainCount=5
autopurge.purgeInterval=1
```

***

## 8. 任务编排设计

### 8.1 工作流设计模式

#### 8.1.1 基础数据同步工作流

```
┌─────────────┐
│  数据抽取     │  ← SeaTunnel 任务（MySQL → 临时表）
└──────┬──────┘
       │
┌──────▼──────┐
│  数据清洗     │  ← SeaTunnel 任务（SQL Transform）
└──────┬──────┘
       │
┌──────▼──────┐
│  数据加载     │  ← SeaTunnel 任务（临时表 → 目标表）
└──────┬──────┘
       │
┌──────▼──────┐
│  数据校验     │  ← Shell/SQL 任务（行数对比、质量检查）
└──────┬──────┘
       │
┌──────▼──────┐
│  完成通知     │  ← 告警/回调通知
└─────────────┘
```

#### 8.1.2 多源汇聚工作流

```
┌──────────┐  ┌──────────┐  ┌──────────┐
│ 源 A 同步  │  │ 源 B 同步  │  │ 源 C 同步  │  ← 并行 SeaTunnel 任务
└─────┬────┘  └─────┬────┘  └─────┬────┘
      │             │             │
      └─────────────┼─────────────┘
                    │
            ┌───────▼───────┐
            │  数据合并       │  ← SeaTunnel 任务（Union/Merge）
            └───────┬───────┘
                    │
            ┌───────▼───────┐
            │  数据写入目标    │  ← SeaTunnel 任务
            └───────────────┘
```

### 8.2 SeaTunnel 任务配置示例

#### 8.2.1 MySQL → ClickHouse 批量同步

```hocon
env {
  parallelism = 4
  job.mode = "BATCH"
}

source {
  Jdbc {
    url = "jdbc:mysql://source-host:3306/source_db?useSSL=false&serverTimezone=Asia/Shanghai"
    driver = "com.mysql.cj.jdbc.Driver"
    user = "readonly_user"
    password = "password"
    table_path = "source_db.orders"
    query = "SELECT * FROM orders WHERE update_time >= '${date_param}'"
    partition_column = "id"
    partition_num = 4
  }
}

transform {
  Filter {
    field = "status"
    condition = "status != 'deleted'"
  }
}

sink {
  ClickHouse {
    host = "clickhouse-host:8123"
    database = "target_db"
    table = "orders"
    username = "default"
    password = "password"
    schema_save_mode = "CREATE_SCHEMA_WHEN_NOT_EXIST"
    data_save_mode = "APPEND_DATA"
    clickhouse.config = {
      clickhouse.bulk_size = 50000
    }
  }
}
```

#### 8.2.2 MySQL CDC 实时同步

```hocon
env {
  parallelism = 2
  job.mode = "STREAMING"
  checkpoint.interval = 10000
}

source {
  MySQL-CDC {
    server-id = 5001
    host = "source-mysql-host"
    port = 3306
    username = "cdc_user"
    password = "password"
    database-pattern = "source_db"
    table-pattern = "orders"
    startup.mode = "INITIAL"
    snapshot.split.size = 10000
    snapshot.fetch.size = 2000
  }
}

sink {
  Elasticsearch {
    hosts = ["es-host:9200"]
    index = "orders_{table}"
    schema_save_mode = "CREATE_SCHEMA_WHEN_NOT_EXIST"
    data_save_mode = "APPEND_DATA"
  }
}
```

### 8.3 定时调度策略

| 场景      | 调度频率      | 说明                    |
| ------- | --------- | --------------------- |
| 全量数据同步  | 每日凌晨（T+1） | 低峰期执行，如 02:00         |
| 增量数据同步  | 每 5-15 分钟 | 使用 CDC 或时间戳增量         |
| 实时数据同步  | 持续运行      | CDC 流模式，配合 Checkpoint |
| 数据质量校验  | 每日同步完成后   | 自动触发                  |
| 报表数据预计算 | 每小时       | 汇总中间结果                |

***

## 9. 监控与告警

### 9.1 CCE 集群监控

| 监控项    | 方式                           | 说明             |
| ------ | ---------------------------- | -------------- |
| Pod 状态 | CCE 控制台 / `kubectl get pods` | 查看 Pod 运行状态    |
| 资源使用   | CCE 监控中心 / Prometheus        | CPU、内存、磁盘      |
| 容器日志   | CCE 日志中心 / kubectl logs      | 查看容器标准输出       |
| 事件监控   | CCE 事件中心                     | Pod 创建、调度、重启事件 |

### 9.2 DS 集群监控

| 指标         | 说明              | 告警阈值      |
| ---------- | --------------- | --------- |
| Master 存活数 | 活跃 Master Pod 数 | < 2 告警    |
| Worker 存活数 | 活跃 Worker Pod 数 | < 2 告警    |
| 等待执行任务数    | 队列中等待的任务数       | > 1000 告警 |
| 任务失败率      | 最近 1 小时任务失败比例   | > 5% 告警   |

### 9.3 告警配置

DolphinScheduler 支持多种告警通道：

| 告警方式  | 配置方式        | 适用场景   |
| ----- | ----------- | ------ |
| 邮件告警  | SMTP 配置     | 任务失败通知 |
| 钉钉机器人 | Webhook URL | 即时通知   |
| 飞书机器人 | Webhook URL | 即时通知   |
| 企业微信  | Webhook URL | 即时通知   |

### 9.4 日志查看

```bash
# 查看 DS Master 日志
kubectl -n dolphinscheduler logs -f ds-master-0

# 查看 DS Worker 日志
kubectl -n dolphinscheduler logs -f ds-worker-0

# 查看 ZooKeeper 日志
kubectl -n dolphinscheduler logs -f zk-0

# 查看 SeaTunnel Master 日志
kubectl -n seatunnel logs -f st-master-0

# 查看 SeaTunnel Worker 日志
kubectl -n seatunnel logs -f st-worker-0
```

***

## 10. 高可用设计

### 10.1 组件高可用策略

| 组件        | 高可用策略                           | 故障恢复           |
| --------- | ------------------------------- | -------------- |
| DS Master | StatefulSet 2 副本 + ZooKeeper 选举 | Pod 自动重启，< 60s |
| DS Worker | StatefulSet 4 副本 + 任务自动迁移       | Pod 自动重启，任务迁移  |
| ZooKeeper | StatefulSet 3 副本 + 奇数节点         | 多数节点存活即可用      |
| ST Master | StatefulSet 2 副本 + Hazelcast 集群 | Pod 自动重启       |
| ST Worker | StatefulSet 4 副本 + 弹性扩展         | Pod 自动重启       |

### 10.2 故障转移流程

```
1. DS Master 故障
   ├─ ZooKeeper 检测到临时节点消失
   ├─ 触发领导者重新选举
   ├─ 新 Master 接管调度
   └─ K8s 自动重启故障 Pod

2. DS Worker 故障
   ├─ Master 检测到 Worker 心跳超时
   ├─ 将该 Worker 上的任务重新分配
   ├─ 其他 Worker 接管执行
   └─ K8s 自动重启故障 Pod

3. ZooKeeper 故障
   ├─ 单节点故障不影响整体服务
   ├─ K8s 自动重启故障 Pod
   └─ 恢复后自动加入集群
```

### 10.3 数据一致性保证

- **DS 层面**: 基于 ZooKeeper 分布式锁保证任务分配一致性
- **SeaTunnel 层面**: Checkpoint 机制保证 Exactly-Once 语义
- **数据库层面**: 现有 MySQL 主从复制

***

## 11. 运维管理

### 11.1 日常运维操作

```bash
# 查看所有 Pod 状态
kubectl -n dolphinscheduler get pods -o wide
kubectl -n seatunnel get pods -o wide

# 查看 Pod 日志
kubectl -n dolphinscheduler logs -f ds-master-0
kubectl -n dolphinscheduler logs -f ds-worker-0

# 进入 Pod
kubectl -n dolphinscheduler exec -it ds-master-0 -- bash

# 查看 ZooKeeper 状态
kubectl -n dolphinscheduler exec zk-0 -- zkServer.sh status

# 查看 SeaTunnel 集群状态
kubectl -n seatunnel exec st-master-0 -- curl http://localhost:8080/hazelcast/rest/cluster

# 重启 Pod
kubectl -n dolphinscheduler delete pod ds-worker-2
```

### 11.2 扩缩容操作

```bash
# DS Worker 扩容（4 -> 8）
kubectl -n dolphinscheduler scale statefulset ds-worker --replicas=8

# ST Worker 扩容（4 -> 8）
kubectl -n seatunnel scale statefulset st-worker --replicas=8

# 缩容
kubectl -n dolphinscheduler scale statefulset ds-worker --replicas=4
```

### 11.3 滚动更新

```bash
# 更新 DS 镜像版本
kubectl -n dolphinscheduler set image statefulset/ds-master \
  master-server=your-registry/dolphinscheduler:3.4.2-new

# 查看更新状态
kubectl -n dolphinscheduler rollout status statefulset/ds-master

# 回滚
kubectl -n dolphinscheduler rollout undo statefulset/ds-master
```

### 11.4 备份策略

| 备份内容         | 频率   | 方式                   |
| ------------ | ---- | -------------------- |
| MySQL 元数据库   | 每日全量 | mysqldump 或 CCE 定时任务 |
| ZooKeeper 数据 | 每日快照 | PVC 快照               |
| K8s 资源清单     | 每次变更 | Git 版本管理             |

***

## 12. 安全设计

### 12.1 访问控制

| 安全维度   | 措施                      |
| ------ | ----------------------- |
| 用户认证   | DS 内置用户系统 / LDAP / OIDC |
| 权限管理   | 项目级、工作流级权限控制            |
| API 安全 | Token 认证、IP 白名单         |
| 数据源安全  | 密码加密存储、敏感信息脱敏           |

### 12.2 网络安全

- 各命名空间内使用 ClusterIP 通信
- ZooKeeper 不对外暴露端口
- DS API Server 通过 Ingress 暴露，配置 HTTPS
- 现有 MySQL 配置白名单，仅允许 CCE Pod CIDR 访问

### 12.3 数据安全

- SeaTunnel 连接器密码使用 K8s Secret 存储
- 敏感数据源使用专用只读账号
- 日志中过滤敏感信息

***

## 13. 常见问题与解决方案

### 13.1 部署问题

| 问题                     | 原因               | 解决方案                           |
| ---------------------- | ---------------- | ------------------------------ |
| Pod 启动失败               | 镜像拉取失败           | 检查 SWR 镜像地址和权限                 |
| ZooKeeper 集群无法选举       | Pod 间 DNS 解析失败   | 确认 Headless Service 配置正确       |
| DS Master 无法连接数据库      | MySQL 连接串或白名单错误  | 检查 CCE Pod CIDR 是否在 MySQL 白名单中 |
| DS Worker 无法注册到 Master | ZooKeeper 地址配置错误 | 确认 `zk-cs` Service DNS 可解析     |

### 13.2 运行问题

| 问题               | 原因               | 解决方案                          |
| ---------------- | ---------------- | ----------------------------- |
| 任务一直处于提交状态       | Master 负载过高或线程池满 | 增加 Master 副本数或调整 exec.threads |
| SeaTunnel 任务 OOM | 并行度过高或数据量过大      | 降低 parallelism，增加 JVM 内存      |
| Pod OOMKilled    | 容器内存超限           | 调整 resources.limits.memory    |
| Pod 频繁重启         | 健康检查失败           | 调整 livenessProbe 参数           |

***

## 14. 附录

### 14.1 端口列表

| 组件               | 端口    | 说明                   |
| ---------------- | ----- | -------------------- |
| DS API Server    | 12345 | RESTful API / Web UI |
| DS Master Server | 5678  | Master 通信            |
| DS Worker Server | 1234  | Worker 通信            |
| ZooKeeper        | 2181  | 客户端连接                |
| ZooKeeper        | 2888  | 集群通信                 |
| ZooKeeper        | 3888  | 选举通信                 |
| SeaTunnel Zeta   | 5801  | Hazelcast 集群通信       |
| SeaTunnel REST   | 8080  | REST API             |

### 14.2 一键部署脚本

```bash
#!/bin/bash
# deploy-all.sh - 一键部署所有组件

NAMESPACE_DS=dolphinscheduler
NAMESPACE_ST=seatunnel
REGISTRY=swr.cn-north-4.myhuaweicloud.com/your-ns

echo "=== 1. 创建命名空间 ==="
kubectl create ns ${NAMESPACE_DS} --dry-run=client -o yaml | kubectl apply -f -
kubectl create ns ${NAMESPACE_ST} --dry-run=client -o yaml | kubectl apply -f -

echo "=== 2. 部署 ZooKeeper ==="
kubectl apply -f zk-configmap.yaml
kubectl apply -f zk-headless-svc.yaml
kubectl apply -f zk-client-svc.yaml
kubectl apply -f zk-statefulset.yaml
kubectl -n ${NAMESPACE_DS} wait --for=condition=ready pod/zk-0 --timeout=120s
kubectl -n ${NAMESPACE_DS} wait --for=condition=ready pod/zk-1 --timeout=120s
kubectl -n ${NAMESPACE_DS} wait --for=condition=ready pod/zk-2 --timeout=120s

echo "=== 3. 部署 DS Master ==="
kubectl apply -f ds-master-configmap.yaml
kubectl apply -f ds-master-hs.yaml
kubectl apply -f ds-api-svc.yaml
kubectl apply -f ds-master-statefulset.yaml
kubectl -n ${NAMESPACE_DS} wait --for=condition=ready pod/ds-master-0 --timeout=120s
kubectl -n ${NAMESPACE_DS} wait --for=condition=ready pod/ds-master-1 --timeout=120s

echo "=== 4. 部署 DS Worker ==="
kubectl apply -f ds-worker-configmap.yaml
kubectl apply -f ds-worker-statefulset.yaml
kubectl -n ${NAMESPACE_DS} wait --for=condition=ready pod/ds-worker-0 --timeout=120s

echo "=== 5. 部署 ST Master ==="
kubectl apply -f st-master-configmap.yaml
kubectl apply -f st-hs.yaml
kubectl apply -f st-master-svc.yaml
kubectl apply -f st-master-statefulset.yaml
kubectl -n ${NAMESPACE_ST} wait --for=condition=ready pod/st-master-0 --timeout=120s
kubectl -n ${NAMESPACE_ST} wait --for=condition=ready pod/st-master-1 --timeout=120s

echo "=== 6. 部署 ST Worker ==="
kubectl apply -f st-worker-configmap.yaml
kubectl apply -f st-worker-statefulset.yaml
kubectl -n ${NAMESPACE_ST} wait --for=condition=ready pod/st-worker-0 --timeout=120s

echo "=== 部署完成 ==="
echo "DS Web UI: http://<cce-ingress-ip>:12345/dolphinscheduler"
echo "默认账号: admin / dolphinscheduler123"
```

### 14.3 参考链接

- [华为云 CCE 文档](https://support.huaweicloud.com/cce/)
- [Apache DolphinScheduler 官方文档](https://dolphinscheduler.apache.org/zh-cn/docs)
- [Apache SeaTunnel 官方文档](https://seatunnel.apache.org/docs)
- [DolphinScheduler K8s 部署](https://github.com/apache/dolphinscheduler/tree/dev/deploy/kubernetes)
- [SeaTunnel K8s 部署](https://github.com/apache/seatunnel/tree/dev/deploy/kubernetes)

### 14.4 版本兼容性矩阵

| DS 版本 | SeaTunnel 版本 | MySQL 版本 | ZooKeeper 版本 | JDK 版本 |
| ----- | ------------ | -------- | ------------ | ------ |
| 3.4.2 | 2.3.13       | 8.0+     | 3.8+         | 11     |
| 3.4.1 | 2.3.13       | 8.0+     | 3.8+         | 11     |
| 3.4.0 | 2.3.12+      | 8.0+     | 3.8+         | 11     |

***

> **文档维护**: 本文档应根据实际部署和运维经验持续更新。\
> **版本记录**: v2.0 - 2026-06-16 更新为华为云 CCE StatefulSet 容器化部署方案


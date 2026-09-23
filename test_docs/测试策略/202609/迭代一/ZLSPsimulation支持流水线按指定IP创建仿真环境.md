1.	支持各业务部分的CICD流水线对接openlibing-simulation时，能够指定自管理的实验室物理机IP，确保仿真任务部署在指定机器上，消除跨部门问题边界不清的风险。 
2.	覆盖API接口如下：（wiki：https://wiki.huawei.com/domains/3627/wiki/8/WIKI2026061511466357 ）
接口	方法 路径	功能
1. 创建 QEMU自动化任务	POST /gateway/openlibing-simulation/simulation/qemu/auto/task	创建自动化任务
2.openlibing-simulation	openlibing-simulation支持CICD流水线按指定IP创建仿真环境	
3.	核心参数说明
创建任务必填参数：
- createBy - 创建人
- eimulationSceneId - 模拟场景（如18表示灵衢通算MatrixServer仿真）
- productName - 项目名称
- community - 所属社区
- config - 任务配置（包含serverIp、nodeNumber、scene、numaCpu、engineName）
任务状态枚举：
- DISPATCHING - 资源调度中
- FAILED - 失败
- READY - 环境就绪，任务执行成功
- ENDED - 已结束，正常关闭
- CLOSED - 已关闭，非正常关闭
4.  产品资料测试
本次版本设计wiki资料刷新，验证通过。
WIKI链接：https://wiki.huawei.com/domains/3627/wiki/8/WIKI2026061511466357

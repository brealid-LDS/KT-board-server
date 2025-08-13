# KT-board-server

client ID: client_group, client_name  
client 参数: 是否开启各项功能, heart-beat(比如5s)(10倍时间之后显示下线)  
client 属性: CPU 占用, 内存占用, 存储占用(及监控存储列表), GPU占用  

一些方法:
/<key-path>/clear-client 清除所有服务器缓存  
/<key-path>/register-client 注册, 返回一个汇报 token  
/<key-path>/heart-beat 汇报当前状态  

服务端参数存储位置: config.json (参考: config_example.json)
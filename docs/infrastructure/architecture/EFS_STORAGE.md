# EFS存储架构

## 设计

整个git仓库存储在EFS，所有EC2实例共享：

```
/mnt/efs/
├── nexus-ai-repo/     # 完整git仓库（所有实例共享）
│   ├── .git/
│   ├── api/
│   ├── agents/
│   ├── tools/
│   └── projects/
└── projects/          # 用户项目数据（向后兼容）
```

## 优势

- **性能**: 只clone一次，后续实例0秒启动
- **一致性**: 所有实例使用相同代码版本
- **节约**: 每个实例节省336MB磁盘和网络带宽

## 实现

EC2实例通过symlink访问EFS中的代码：
```bash
/opt/nexus-ai -> /mnt/efs/nexus-ai-repo
```

第一个实例clone，后续实例直接使用。

## 更新代码

在bastion上执行：
```bash
cd /mnt/efs/nexus-ai-repo
git pull origin main
```

所有API实例立即使用新代码（需重启容器）。

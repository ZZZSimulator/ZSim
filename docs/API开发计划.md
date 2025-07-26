# ZZZ模拟器API开发计划文档

## 当前API进度总览

### 已完成API

#### 会话管理API (session_op.py)
- ✅ `POST /api/sessions/` - 创建新会话
- ✅ `GET /api/sessions/` - 获取所有会话列表
- ✅ `GET /api/sessions/{session_id}` - 获取单个会话详情
- ✅ `GET /api/sessions/{session_id}/status` - 获取会话状态
- ✅ `POST /api/sessions/{session_id}/run` - 启动会话模拟
- ✅ `POST /api/sessions/{session_id}/stop` - 停止会话（基础实现）
- ✅ `PUT /api/sessions/{session_id}` - 更新会话信息（根据代码结构推测）
- ✅ `DELETE /api/sessions/{session_id}` - 删除会话（根据代码结构推测）

#### 系统健康检查
- ✅ `GET /health` - 系统健康检查

## 综合API开发计划

根据WebUI功能模块和现有API分析，以下是详细的API开发计划：

### 1. 角色配置API

#### 数据管理API
- ✅ `GET /api/characters/` - 获取所有可用角色列表
- ✅ `GET /api/characters/{name}/info` - 获取角色详细信息
- ✅ `GET /api/weapons/` - 获取所有可用武器列表
- ✅ `GET /api/equipments/` - 获取所有可用装备列表
- ✅ `GET /api/equipments/sets` - 获取装备套装信息

#### 角色配置API
- ✅ `POST /api/characters/{name}/configs` - 为指定角色创建配置
- ✅ `GET /api/characters/{name}/configs` - 获取指定角色的所有配置
- ✅ `GET /api/characters/{name}/configs/{config_name}` - 获取指定角色的特定配置
- ✅ `PUT /api/characters/{name}/configs/{config_name}` - 更新指定角色的特定配置
- ✅ `DELETE /api/characters/{name}/configs/{config_name}` - 删除指定角色的特定配置

#### 角色配置数据模型
开启模拟时，配置名称不属于模拟项
需要一个单独的数据表储存角色配置
```json
{
  "config_name": "配置名称",
  "name": "角色",
  "weapon": "音擎",
  "weapon_level": 1,
  "cinema": 0,
  "crit_balancing": false,
  "crit_rate_limit": 0.95,
  "scATK_percent": 0,
  "scATK": 0,
  "scHP_percent": 0,
  "scHP": 0,
  "scDEF_percent": 0,
  "scDEF": 0,
  "scAnomalyProficiency": 0,
  "scPEN": 0,
  "scCRIT": 0,
  "scCRIT_DMG": 0,
  "drive4": "攻击力%",
  "drive5": "攻击力%",
  "drive6": "攻击力%",
  "equip_style": "4+2",
  "equip_set4": "套装名称",
  "equip_set2_a": "套装名称"
}
```

### 2. 敌人配置API

#### 敌人数据API
- ✅ `GET /api/enemies/` - 获取所有可用敌人列表
- ✅ `GET /api/enemies/{enemy_id}/info` - 获取敌人详细信息

#### 敌人配置API
- ✅ `POST /api/enemy-configs/` - 创建敌人配置
- ✅ `GET /api/enemy-configs/` - 获取所有敌人配置
- ✅ `GET /api/enemy-configs/{config_id}` - 获取特定敌人配置
- ✅ `PUT /api/enemy-configs/{config_id}` - 更新敌人配置
- ✅ `DELETE /api/enemy-configs/{config_id}` - 删除敌人配置

#### 敌人配置数据模型
```json
{
  "enemy_index": 0,
  "adjustment_id": 22014,
  "difficulty": 8.74
}
```

### 3. APL相关API

#### APL模板API
- [x] `GET /api/apl/templates` - 获取APL模板

#### APL配置API
- [x] `POST /api/apl/configs/` - 创建APL配置
- [x] `GET /api/apl/configs/` - 获取所有APL配置
- [x] `GET /api/apl/configs/{config_id}` - 获取特定APL配置
- [x] `PUT /api/apl/configs/{config_id}` - 更新APL配置
- [x] `DELETE /api/apl/configs/{config_id}` - 删除APL配置

#### APL文件管理API
- [x] `GET /api/apl/files` - 获取所有APL文件列表
- [x] `POST /api/apl/files` - 创建新APL文件
- [x] `GET /api/apl/files/{file_id}` - 获取APL文件内容
- [x] `PUT /api/apl/files/{file_id}` - 更新APL文件内容
- [x] `DELETE /api/apl/files/{file_id}` - 删除APL文件

#### APL语法检查API
- [x] `POST /api/apl/validate` - 验证APL语法
- [x] `POST /api/apl/parse` - 解析APL代码

### 4. 模拟配置相关API

#### 模拟功能API
- [ ] `GET /api/simulation/functions` - 获取可用的模拟功能列表
- [ ] `GET /api/simulation/modes` - 获取可用的运行模式

#### 模拟配置API
- [ ] `POST /api/sessions/{session_id}/simulation-configs` - 为指定会话创建模拟配置
- [ ] `GET /api/sessions/{session_id}/simulation-configs` - 获取指定会话的模拟配置
- [ ] `GET /api/sessions/{session_id}/simulation-configs/{config_id}` - 获取指定会话的特定模拟配置
- [ ] `PUT /api/sessions/{session_id}/simulation-configs/{config_id}` - 更新指定会话的特定模拟配置
- [ ] `DELETE /api/sessions/{session_id}/simulation-configs/{config_id}` - 删除指定会话的特定模拟配置

#### 模拟配置数据模型
```json
{
  "stop_tick": 3600,
  "mode": "普通模式（单进程）",
  "parallel_config": {
    "adjust_char": 1,
    "adjust_sc": {
      "enabled": true,
      "sc_range": [0, 75],
      "sc_list": ["攻击力%", "暴击率"],
      "remove_equip_list": ["暴击率"]
    },
    "adjust_weapon": {
      "enabled": false,
      "weapon_list": []
    }
  }
}
```

### 5. 模拟结果相关API

#### 结果管理API
- [ ] `GET /api/simulation/results` - 获取所有结果列表
- [ ] `GET /api/simulation/results/{result_id}` - 获取特定结果详情
- [ ] `PUT /api/simulation/results/{result_id}/rename` - 重命名结果
- [ ] `DELETE /api/simulation/results/{result_id}` - 删除结果
- [ ] `GET /api/simulation/results/{result_id}/export` - 导出结果数据

#### 结果分析API
- [ ] `GET /api/simulation/results/{result_id}/damage` - 获取伤害分析数据
- [ ] `GET /api/simulation/results/{result_id}/buffs` - 获取Buff分析数据
- [ ] `GET /api/simulation/results/{result_id}/summary` - 获取结果摘要

### 6. 数据分析相关API

#### 数据处理API
- [ ] `POST /api/analysis/damage` - 分析伤害数据
- [ ] `POST /api/analysis/buff` - 分析buff数据
- [ ] `POST /api/analysis/parallel` - 分析并行模式数据
- [ ] `POST /api/analysis/charts` - 生成图表数据

### 7. 系统管理相关API

#### 配置管理API
- [ ] `GET /api/config/system` - 获取系统配置
- [ ] `PUT /api/config/system` - 更新系统配置
- [ ] `GET /api/config/default` - 获取默认配置

#### 版本检查API
- [ ] `GET /api/system/version` - 获取当前版本信息
- [ ] `GET /api/system/updates` - 检查更新

#### 资源监控API
- [ ] `GET /api/system/resources` - 获取系统资源使用情况
- [ ] `GET /api/system/processes` - 获取运行中的进程信息

## 技术实现建议

### 目录结构
```
zsim/api_src/
├── routes/
│   ├── __init__.py
│   ├── session_op.py          # 已完成
│   ├── character_config.py    # 角色配置相关
│   ├── enemy_config.py        # 敌人配置相关
│   ├── apl.py                 # APL相关
│   ├── simulation.py          # 模拟器相关
│   ├── result.py              # 结果管理相关
│   └── system.py              # 系统管理相关
├── services/
│   ├── database/
│   │   ├── session_db.py      # 已完成
│   │   ├── character_db.py    # 角色配置数据
│   │   ├── enemy_db.py        # 敌人配置数据
│   │   ├── apl_db.py          # APL文件数据
│   │   ├── config_db.py       # 配置数据
│   │   └── result_db.py       # 结果数据
│   ├── character_service.py   # 角色配置业务逻辑
│   ├── enemy_service.py       # 敌人配置业务逻辑
│   ├── apl_service.py         # APL业务逻辑
│   ├── simulation_service.py  # 模拟器业务逻辑
│   └── result_service.py      # 结果管理业务逻辑
└── models/
    ├── character/
    ├── enemy/
    ├── apl/
    ├── simulation/
    └── result/
```

### 开发优先级

#### 高优先级（核心功能）
1. 角色配置相关API ✅
2. 模拟器配置相关API
3. 结果管理API
4. APL配置API

#### 中优先级
1. 敌人配置API ✅
2. 数据分析API
3. 系统管理API
4. APL语法检查API

#### 低优先级
1. APL编辑器高级功能
2. 资源监控API

### 数据模型设计

需要为以下实体创建数据模型：
- Character（角色）
- Weapon（武器）
- Equipment（装备）
- Enemy（敌人）
- APLFile（APL文件）
- SimulationConfig（模拟配置）
- SimulationResult（模拟结果）

### 错误处理规范

所有API应遵循统一的错误响应格式：
```json
{
  "code": 错误码,
  "message": "错误描述",
  "data": null
}
```

### 认证授权

当前为本地应用，可暂不考虑认证，但建议预留接口：
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/status`

## 测试计划

### 单元测试
- 每个API端点的单元测试
- 数据验证测试
- 错误处理测试

### 集成测试
- 端到端功能测试
- 并发请求测试
- 性能测试

### 测试覆盖率目标
- 代码覆盖率：≥80%
- API覆盖率：100%
- 关键路径测试：100%

## 部署计划

### 开发阶段
1. 本地开发环境搭建
2. API开发
3. 单元测试
4. 集成测试

### 生产部署
1. Docker容器化
2. 性能优化
3. 监控配置
4. 文档完善

## 注意事项

1. **性能考虑**：并行计算API需要特别注意并发处理
2. **数据一致性**：确保数据库操作的事务性
3. **错误恢复**：模拟任务失败时的重试机制
4. **缓存策略**：合理使用缓存提高性能
5. **版本控制**：API版本管理策略

## 后续扩展

- WebSocket支持实时更新
- GraphQL API
- 插件系统
- 多语言支持
- 云端部署支持
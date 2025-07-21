<style>
body {
    font-family: "HarmonyOS Sans SC", SimSun, sans-serif;
    border: 2px solid red !important;
}
code, pre {
    font-family: Consolas, Monaco, monospace;
}
/* 详情展开组件样式 */
.details-summary {
    text-indent: 2em;
    color: gray;
    cursor: pointer;
}
.details-content {
    text-indent: 2em;
    color: gray;
    white-space: pre-line;
    margin: 0.5em 0;
}
/* 列专属居中样式 */
/* 列表1、2列居中*/
.col-center-1-2 th:nth-child(1),
.col-center-1-2 td:nth-child(1),
.col-center-1-2 th:nth-child(2),
.col-center-1-2 td:nth-child(2)
 {
  text-align: center;
  vertical-align: middle;
}
/* 列表1、2、3列居中*/
.col-center-1-2-3 th:nth-child(1),  
.col-center-1-2-3 td:nth-child(1),
.col-center-1-2-3 th:nth-child(2),
.col-center-1-2-3 td:nth-child(2),
.col-center-1-2-3 th:nth-child(3),
.col-center-1-2-3 td:nth-child(3)
 {
  text-align: center;
  vertical-align: middle;
}
.col-center-1-7 th:nth-child(1),
.col-center-1-7 td:nth-child(1),
.col-center-1-7 th:nth-child(2),
.col-center-1-7 td:nth-child(2),
.col-center-1-7 th:nth-child(3),
.col-center-1-7 td:nth-child(3),
.col-center-1-7 th:nth-child(4),
.col-center-1-7 td:nth-child(4),
.col-center-1-7 th:nth-child(5),
.col-center-1-7 td:nth-child(5),
.col-center-1-7 th:nth-child(6),
.col-center-1-7 td:nth-child(6),
.col-center-1-7 th:nth-child(7),
.col-center-1-7 td:nth-child(7)
{
  text-align: center;
  vertical-align: middle;
}

/* 表格特殊宽度 */
.table-width-80 {
    display: inline-block;
    width: 80px;
    white-space: nowrap;
}
.table-width-120 {
    display: inline-block;
    width: 120px;
    white-space: nowrap;
}
.table-width-300 {
    display: inline-block;
    width: 300px;
    white-space: nowrap;
}
.table-width-50 {
    display: inline-block;
    width: 50;
    white-space: nowrap;
}
p {
    text-indent: 2em;
    margin: 0.5em 0; /* 可选：添加段落间距 */
}

/* 详情组件中的段落特殊处理（避免双重缩进） */
.details-content p {
    text-indent: 0; /* 继承父级缩进 */
    margin: 0.3em 0; /* 调整间距保持美观 */
}

:root {
    --row-color-0: #FFE082;
    --row-color-1: #FFCDD2;
    --row-color-2: #81D4FA;
    --row-color-3: #BBDEFB;
    --row-color-4: #D1C4E9;
    --row-color-5: #29B6F6;

}
.color-0 {
    background-color: var(--row-color-0);
}
.color-1 {
    background-color: var(--row-color-1);
}
.color-2 {
    background-color: var(--row-color-2);
}
.color-3 {
    background-color: var(--row-color-3);
}
.color-4 {
    background-color: var(--row-color-4);
}
.color-5 {
    background-color: var(--row-color-5);
}

/* 颜色标记 */
.color-assault { color: #FFB74D; }
.color-burn { color: #FF7043; }
.color-frostbite { color: #81D4FA; }
.color-frostfrostbite { color:  #42A5F5}
.color-corruption { color: #673AB7; }
.color-shock { color:  #1976D2}
.color-auricink{ color: #F9A825}
.color-str{ color: #9575CD}
.color-bool{ color: #7986CB}
.color-number{ color: #283593}
.color-none{ color: #FF8A65}
.color-enable{ color: #4CAF50}
.color-disable{ color: #BDBDBD}
</style>

# ZSim APL设计书

> #### <b>文档更新日期：2025.7.3</b>


## 0、前言

#### 本文档介绍了ZSim中APL模块的使用方法以及代码语法，以帮助每一位想要寻找更优解的ZSim使用者

> APL（Action Priority List），即战斗优先级序列，是ZZZ Simulator的核心功能，它可以使角色以我们设定好的优先级，完全自动的行动，配合全自动触发的Buff、属性异常、失衡、伤害计算等模块，组成了完整的模拟器。
>
> 本工具仿照了《魔兽世界》的一款战斗模拟器（SimulationCraft） 中的APL功能设计。通过APL，可以对游戏角色的输出流程进行定制化管理，并且，由程序以100%的完成度进行执行。
>
> 我们认为，一份足够优秀、严谨的APL代码，是完全可以复刻玩家的玩法构思和输出思路的，因为构造APL代码的本质就是对输出逻辑的逆向解构。
>
> <details>
>   <summary class="details-summary">APL系统详细介绍</summary>
>   <p class="details-content">通常，针对同一个角色或是队伍的手法讨论，只能基于玩家的感觉来进行，对于“怎么打比较合适”的手法细节讨论，往往得不出一个最终的结论。即使我们能够借助第三方的游戏计算器，让局部总伤计算更加精确，但也最多只能做到局部精确。某个手法或是某种输出策略对于全局战斗的影响，依旧是难以计算和模拟的。</p>
>   <p class="details-content">所以，模拟仿真计算器以及APL脚本应运而生。二者结合，就可以真正实现不同策略之间的公平比较，比如：某角色有能量和豆子两种资源，那么到底是优先打能量资源，还是优先打豆子资源呢？通过APL的控制，我们可以设计两套手法，一套永远先打能量，一套永远先打豆子。APL就好像一个水平超高的玩家，它会清晰、稳定地执行我们设计好的既定手法。</p>
>   <p class="details-content">最终，我们从模拟结果上，可以看到两套手法方案被百分百执行时的输出水平，从而找出其中最优的输出策略。这样的仿真思路，在很多游戏中都能见到，比如Simc、Gscim（原神的模拟仿真软件）等。</p>
>   <p class="details-content">本模拟器（ZZZSim） 的APL功能正是仿照Simc的APL运行逻辑写的。但是在具体的运行上有一些不同。语法上也针对游戏特色进行了一些优化和改动。</p>
> </details>

---

## 1、ZSim中APL模块的运作原理

ZSim的APL模块每次运行时，都会从APL脚本的第一行开始，逐行检验其条件部分，直到找到某一行的所有条件全部通过，就将这一行所指向的技能ID输出给下一步程序。每一行APL代码都只能指向一个动作，但是限制条件可以是多个，同一个动作的限制条件之间用 `|`分隔符进行隔离，这些条件之间都是“与”关系（不要纠结为什么没有用 `&`）。

当前版本，如果激活某动作的条件之间存在“或”关系，则应写多行APL代码。

<details>
   <summary class="details-summary">后续开发方向</summary>
   <p class="details-content">目前，程序只支持“非门”和“与门”，暂不具备解析“或门”的能力。不过，该功能将会是APL功能拓展的首个目标，因为当APL脚本代码涉及到多条件中的多个“或”逻辑时，现有的脚本语法会让APL代码变得非常臃肿冗杂，所以，解析“或”逻辑的功能可以说是迫在眉睫。</p>
</details>

---

## 2、APL代码的载体及其文档结构

APL代码采用toml格式进行记录，为了保证文档能被ZSim成功识别、解析，请保证文档格式符合toml文件的格式要求。**如果使用工具自带APL编辑功能，toml配置会自动完成，如果需要深度了解，可以进一步阅**读：

一份完整的APL文档应该由 **基础信息**、<b>执行条件 </b>、<b>APL代码主体 </b>三个部分构成：

- #### 基础信息：文档名称、注释、作者、创造及修改时间
  
```toml
[general]
title = "APL配置示例"
comment = "这是一个APL配置示例，你可以据此新建新模板"
author = "Yuki Aro"
create_time = "2025-04-15T23:00:00.000+08:00"
latest_change_time = "2025-04-15T23:00:00.000+08:00"
```

基础信息中，create_time和latest_change_time都是程序自动生成和修改的，不需要手动修改。

- #### 执行条件：必选角色、备选角色、各角色配置要求
  
```toml
[characters]
required = [ "零号·安比", "扳机",]
optional = [ "丽娜",]
  
[characters."零号·安比"]
cinema = [ 0, 1, 2, 3, 4, 5, 6,]
weapon = ""
equip_set4 = ""
  
[characters."扳机"]
cinema = 0
weapon = ""
  
[characters."丽娜"]
cinema = [ 0,]
weapon = ""
```

执行条件中的 <b>必选角色 </b>为此份APL运行的最低要求，其中的角色在即将进行的模拟战斗中，是需要上场释放技能的，所以在选择角色界面，我们需要选择全部的必选角色，才能使APL满足运行要求。

而 <b>备选角色 </b>则不同，APL中并未规定Ta们的技能释放逻辑，全程不会上场释放技能，只作为激活组队被动的插件或是引擎、驱动盘套装的触发器入队。所以，即使在初始化时没有选择备选角色，也不影响整份APL的运行。

 在角色配置要求中，<b>cinema </b>代表了角色影画，<b>weapon </b>代表引擎，<b>equip_set4 </b>代表驱动盘套装。在这些字段中，我们可以输入与当前APL逻辑相匹配的影画和配装情况。比如，在一份适配2~4画、专武+4雷暴配装的柳的APL文档中，柳的对应配置代码应为：

```toml
 [characters."柳"]
cinema = [2, 3, 4]
weapon = "时流贤者"
equip_set4 = "雷暴重金属"
```

而当别的ZSim用户拿着这一份APL文档进行模拟时，ZSim会首先检查角色的配置情况，如果有角色的配置不符合文档要求，则会提示用户修改角色的配置再进行模拟。

- #### APL代码主体
  
```python-repl
# 扳机逻辑
# 扳机补充决意值逻辑：
# 连击逻辑：
1361|action+=|1361_SNA_1|attribute.1361:special_state→狙击姿态==True|attribute.1361:special_resource<100|status.enemy:stun_pct<=0.7
# 启动逻辑
1361|action+=|1361_SNA_0|attribute.1361:special_resource<5|status.enemy:stun==False
  
# 失衡期逻辑：
#连携技释放逻辑
1361|action+=|1361_QTE|status.enemy:QTE_triggered_times==0|status.enemy:single_qte!=None|special.preload_data:operating_char!=1361
1381|action+=|1381_QTE|status.enemy:single_qte!=None|special.preload_data:operating_char!=1381
  
.........
```

AP代码主体记录了角色的输出逻辑，它主要由一行行的APL语句构成。

### 2.1、单行APL语句基本构成

```python
# 注释 xxxxxxxxxxxxxxxxxxx
动作角色|动作类型|动作ID|条件单元1|条件单元2|条件单元3|条件单元4……
```

1. **动作角色：** 执行动作的主体，通常为角色的CID
2. **动作类型：** APL动作的类型或是策略，释放技能/进行进攻交互等……
3. **动作ID：** 具体的动作ID，通常为技能的skill tag
4. **条件单元：** 条件单元是APL脚本的核心，通常是对角色、敌人或者环境的状态（如资源、冷却时间、敌人状态等）的判断。只有当同一行中所有的条件都满足时，该行APL才会被执行。
5. **注释：** 使用 `#` 开头的行作为注释，不会被解析器执行，写APL时，应对每一行的代码都进行标注，写明该动作的条件以及逻辑层次。对于比较复杂或是反常的优先级结构，则更应通过#进行说明。
  
   接下来，让我们来看看一行具体的APL代码：

```python
#满豆自动放满蓄力普攻
1091|action+=|1091_SNA_3|attribute.1091:special_resource==6
```

    这行代码的意思是：雅将在6个豆子时候使用满蓄力普攻。

 **参数解释：**

<table class="col-center-1-2">
  <tr>
    <th style="width: 240px">参数</th>
    <th><span class="table-width-80">类型</span></th>
    <th>备注</th>
  </tr>
  <tr>
    <td><code>#</code></td>
    <td>注释</td>
    <td>用于解释该行APL的作用，不是必须的。</td>
  </tr>
  <tr>
    <td><code>1091</code></td>
    <td>动作角色</td>
    <td>在ZSim内部，雅的数字ID为1091</td>
  </tr>
  <tr>
    <td><code>action+=</code></td>
    <td>动作类型</td>
    <td>action类型，即"主动动作类型"，可以简单理解为"打出一个技能"</td>
  </tr>
  <tr>
    <td><code>1091_SNA_3</code></td>
    <td>动作ID</td>
    <td>技能ID，或填写wait代表什么都不做。</td>
  </tr>
  <tr>
    <td><code>attribute.1091:special_resource==6</code></td>
    <td>条件单元</td>
    <td>控制了本行APL是否执行的限制条件</td>
  </tr>
</table>

### 2.2、动作类型介绍
除了普通类型动作以外，还可以通过添加一些后缀，来丰富APL的策略，<br><p><font color="red"><b>但请注意，这些带后缀的特殊动作类型尚处于开发阶段，开发团队尚不能保证其稳定性和正确性，<br><p>不同策略在面对合轴、QTE、大招等技能抢队时可能会做出完全不同的表现，其中，APL的大部分行为都是合理且符合预期的，但是也一定会存在一些Bug导致APL在策略冲突的情况下做出错误决策。<br><p>总之，我们团队会持续关注、开发这一功能，直至它彻底稳定。</b></font>
<table class="col-center-1-7">
  <tr>
    <th style="width: 240px">动作类型</th>
    <th><span class="table-width-80">稳定度</span></th>
    <th>解释</th>
  </tr>
  <tr>
    <td><code>action+=</code></td>
    <td><font color="green">高</font></td>
    <td>最普通类型的APL</td>
  </tr>
  <tr>
    <td><code>action.no_swap_cancel+=</code></td>
    <td><font color="orange">中</font></td>
    <td><b>避免合轴</b>策略，即哪怕时间和其他条件均满足，可以进行合轴，当前APL也不会放行，除非上一个动作彻底结束</td>
  </tr>
  <tr>
    <td><code>action.atk_response_positive+=</code></td>
    <td  rowspan="2"><font color="red">低</font></td>
    <td><b>“积极地进行进攻响应”</b>：即角色会在怪物红、黄光亮起后的<b>最早时间</b>进行响应（闪避或是弹刀）</td>
  </tr>
  <tr>
    <td><code>action.atk_response_balance+=</code></td>
    <td><b>“平衡地进行进攻响应”</b>：即角色会在怪物红、黄光亮起后的<b>最晚时间</b>进行响应（闪避或是弹刀）</td>
  </tr>
</table>

---

## 3、APL语法：通用特殊字符

<table class="col-center-1-2-3">
  <thead>
    <tr>
      <th style="width: 80px">符号</th>
      <th>含义</th>
      <th><span class="table-width-120">示例</span></th>
      <th><span class="table-width-300">实例解释</span></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><code>|</code></td>
      <td>分隔符，用于分割不同的条件单元。虽然<code>|</code>符号自身具有“或”的语义，<br>但是在APL中，它只作为分隔符使用，被它分隔的各个条件单元之间是“与”关系。</td>
      <td>条件单元1|条件单元2</td>
      <td>需要同时满足条件1<strong>和</strong>条件2</td>
    </tr>
    <tr>
      <td><code>!</code></td>
      <td>“非”，即表达条件的反义。由于APL语法中比较符必须存在（包括!=），实际使用量不大</td>
      <td><code>!action.after: index==1091_SNA_3</code></td>
      <td>上一个技能的ID<strong>不是</strong>1091_SNA_3</td>
    </tr>
    <tr>
      <td><code>→</code></td>
      <td>复杂数据集中的子项名称（特殊字符，中文输入法输入"You"打出）</td>
      <td><code>attribute.1300:special_state→醉花月云转可用次数>=0</code></td>
      <td>青衣的特殊状态中的<strong>醉花月云转可用次数</strong>≥0</td>
    </tr>
  </tbody>
</table>

---

## 4、APL语法：书写规范

在编写APL代码时，应遵守以下语法规范：

> - 每行仅定义一个动作，条件可以是多个，但是条件之间必须是“与”关系；
> - APL代码对大小写敏感，请确保大小写的正确性；
> - 同行的不同条件之间，严格使用 `|`符号分隔；
> - 整行代码应不含无意义空格；
> - 在使用文本类信息（比如技能ID、Buff的ID等）时直接输入，不需要单、双引号；
> - 优先级高的APL应总是处于上方；
> - 反义符号 `!`应使用英文字体，嵌套结构索引则应使用完整字符 `→`，而不要使用 `->；
> - ........

---

## 5、APL语法：条件单元全参数详解

    前面已经介绍过，单行APL包含了若干个条件单元，而一个完整的APL条件单元共有5个部分组成：

**[条件类型] . [检索目标] : [检索内容]  [比较符(==/!=/>/</>=/<=)]  [检索值]**

1、<b>条件类型：</b>检查何种类型的条件

2、<b>检索目标：</b>检查谁

3、<b>检索内容：</b>查什么属性/状态

4、<b>比较符 </b>

5、<b>检索值：</b>通过判定所需要的 属性/状态的值

APL中每一种 <b>条件类型 </b>都有各自的 <b>检索目标 </b>，而不同的 <b>检索目标 </b>又有着各自的 <b>检索内容 </b>，所以，我将以 <b>条件类型 </b>为主线，依次展开五种APL的具体语法和使用方法。而在正式开始之前，有一些内容需要提前说明。

---

- #### 检索目标
  

目前，APL语法支持的通用检索目标共有3类，分别是 <b>角色（CID）</b>，<b>队伍（team）</b>，<b>敌人（enemy）</b>，其中，

<b>角色 </b>的检索需要填入角色对应的4位整数ID码：CID（比如，雅在ZSim中的CID就是1091），所以在下面的全参数详解中，我也将用“CID”来指代角色ID，反之，如果在 <b>检索目标 </b>的单元格中看到了“CID”，那么就意味着此处需要填写4位数角色ID码，而不是字母“CID”；

<b>队伍 </b>的检索目前只会在 <b>action </b>类条件中被用到，这里只需要填写“team”字符即可；

<b>敌人 </b>的检索与 <b>队伍 </b>相同，也只需要填写对应的字符“enemy”即可。

---

- #### 比较类型
  

由于 <b>比较符 </b>与 <b>检索值 </b>的具体组合不可能穷举，为了方便理解，我们将APL中所有的比较行为分为四类。

1、<font class="color-bool"><b>布尔值比较：</b></font>此类条件比较符只有两种：<code>==</code>以及 <code>!=</code>，与其对应的检索值为：<code>True </code>和 <code>False </code>；

2、<font class="color-number"><b>数值比较：</b></font>此类条件比较支持6种类数值比较符：<code>></code>、<code><</code>、<code>==</code>、<code>!=</code>、<code>>=</code>、<code><=</code>，与之对应的检索值类型为：<code>int </code>、<code>float </code>

3、<font class="color-none"><b>None比较：</b></font>此类条件比较符只有两种：<code>==</code>以及 <code>!=</code>，与其对应的检索值为：<code>None </code>

4、<font class="color-str"><b>字符比较：</b></font>此类条件比较符只有两种：<code>==</code>以及 <code>!=</code>，与其对应的值检索类型为：<code>str </code>

---

- #### 检索内容
  

APL语法中的检索内容种类繁多，其中的绝大部分都只要填入表中对应的字符即可，只有以下几种检索内容，我会使用指定单次进行替代：

1、<b>buff_index </b>：该检索内容被使用于 <b>Buff类条件 </b>中，表示填入一个Buff的索引，也是Buff的名字，通常，Buff的index是一长串带有中文的字符，比如 <b>“Buff-角色-丽娜-核心被动-穿透率”</b>，顺带一提，Zsim中的Buff名都是这种格式，非常直观，光看名字大概就能知道Buff的作用。

2、<b>skill_tag </b>：该检索内容被使用于 <b>action </b>类条件中，指的是某技能的具体ID，如ZSim中，雅的满蓄力普攻的ID为“1091_SNA_3”。

---

> 接下来，让我们正式开始。
>
> ### ▶5.1 动作类条件——action
>
> <b>action </b>类条件的检索目标可以分为两类：检索角色或者检索全队。
>
> <table class="col-center-1-2-3">
> <tr>
> <td><b>条件类型</b></td>
> <td><b>分隔符</b></td>
> <td><b>检索目标</b></td>
> <td style="text-align: center"><b>含义</b></td>
> <td><b>开发现状</b></td>
> </tr>
> <tr>
> <td rowspan="2"><code>action</code></td>
> <td rowspan="6"><code>.</code></td>
> <td><code>CID</code></td>
> <td>检索角色<code>CID</code>的动作栈，检查其过去动作</td>
> <td><span class="color-enable">可用</span></td>
> </tr>
> <tr>
> <td><code>team</code></td>
> <td>检索全队的动作栈，检查全队过去的动作</td>
> <td ><span class="color-disable">暂不可用</span></td>
> </tr>
> </table>
>
> > <details>
> > <summary class="details-summary">角色动作栈与全队动作栈的区别</summary>
> > <p class="details-content">在Zsim中，角色和全队都有各自的动作栈。每位角色都将记住自己最近的3个动作，而全队则将记住最近的5个动作。</p>
> >  <p class="details-content">注意：这里的动作不仅包括主动动作，也包括一些自动触发的被动动作，比如板机的协同攻击、耀佳音的震音、薇薇安的落羽生花等，这一点非常重要，这关系到角色能否顺利实现玩家预设的连招。</p>  
> > <p class="details-content">由于ZSim是支持合轴操作的，所以，在个人动作栈中相邻的两个动作，在全队动作栈中很可能不相邻——比如角色在相邻的两段平A之间，触发了扳机的协同攻击，那么在全队动作栈中，就会出现 平A 扳机协同攻击 平A的情况。</p>  
> >  <p class="details-content">所以如果你希望雅在自己的第三段平A后衔接强化E，则应该让APL直接检索雅的个人动作栈，而非全队动作栈。</p>
> > </details>
>
>
> <b>action </b>类型的全参数详解如下表：
>
> <table class="col-center-1-7">
> <tr>
> <td><b>检索目标</b></td>
> <td><b>分隔符</b></td>
> <td><b>检索内容</b></td>
> <td><b>比较类型</b></td>
> <td><b>解释</b></td>
> </tr>
> <tr>
> <td rowspan="7">CID</td>
> <td rowspan="8"><code>:</code></td>
> <td><code>strict_linked_after</code></td>
> <td rowspan="4"><span class="color-str">字符比较</span></td>
> <td>强衔接判定，语义为：<b>“严格衔接于……动作后”</b>，<br>
> 此类APL条件单元的放行不仅需要skill_tag符合要求，还需要上一个动作刚好结束</td>
> </tr>
> <tr>
> <td><code>lenient_linked_after</code></td>
> <td>弱衔接判定，语义为：<b>“衔接于……动作后”，</b><br>
> 此类APL条件单元只需要skill_tag符合就会放行</td>
> </tr>
> <tr>
> <td><code>positive_linked_after</code></td>
> <td>积极衔接判定，语义为：<b>“尝试衔接于……动作后”，</b><br>
> 本类APL与<code>lenient_linked_after</code>功能基本相同，但是语义上更好理解。</td>
> </tr>
> <tr>
> <td><code>is_performing</code></td>
> <td>正在释放判定，语义为：<b>“角色正在释放……动作”，</b><br>
> </tr>
> <tr>
> <td><code>first_action</code></td>
> <td rowspan="3"><span class="color-bool">布尔值比较</span></td>
> <td>首个动作判定，语义为：<b>“角色是否没有释放过任何技能？”</b><br></td>
> </tr>
> <tr>
> <td><code>during_parry</code></td>
> <td>招架交互判定，语义为：<b>“角色当前是否正处于招架状态？<br>（招架——招架成功——被击退）”</b></td>
> </tr>
> <tr>
> <td><code>assault_aid_enable</code></td>
> <td>突击支援可用，语义为：<b>“角色是否满足使用突击支援的前置条件？”<br>（成功招架一次攻击并且被击退状态已经消退）</b></td>
> </tr>
> <tr>
> <td class="color-disable">team<br>（弃用）</td>
> <td class="color-disable">skill_tag</td>
> <td class="color-str">字符比较</td>
> <td>team的skill_tag属性本来用于检查“全队的上一个技能”，但由于全队动作栈会受到合轴以及各种协同攻击插队的影响，导致“上一个技能”的检索结果经常在短时间内频繁更替，这会严重误导APL的判定，让本该放行的技能阻塞，或者让本该被跳过的技能执行。所以在古早的开发版本中，APL模块的<b>action.team:skill_tag==xxxx</b>语句就随着合轴功能的更新而被废弃了</td>
> </tr>
> </table>
>
> ---
>
> ### ▶5.2 状态类条件——status
>
> status类型的全参数详解如下表：
>
> <table class="col-center-1-7">
> <tr>
> <td><b>检索目标</b></td>
> <td><b>分隔符</b></td>
> <td><b>检索内容</b></td>
> <td><b>分隔符</b></td>
> <td><b>嵌套结构键值链</b></td>
> <td><b>比较类型</b></td>
> <td><b>解释</b></td>
> </tr>
> <tr>
> <td rowspan="20"><code>enemy</code></td>
> <td rowspan="20"><code>:</code></td>
> <td><code>stun</code></td>
> <td rowspan="20">无分隔符</td>
> <td rowspan="20">无键值链</td>
> <td><span class="color-bool">布尔值比较</span></td>
> <td>敌人是否处于失衡状态</td>
> </tr>
> <tr>
> <td><code>stun_pct</code></td>
> <td><span class="color-number">数值比较</span></td>
> <td>敌人当前的失衡百分比</td>
> </tr>
> <tr>
> <td><code>QTE_triggered_times</code></td>
> <td><span class="color-number">数值比较</span></td>
> <td>敌人已经激发过几次连携技</td>
> </tr>
> <tr>
> <td><code>QTE_activation_available</code></td>
> <td><span class="color-bool">布尔值比较</span></td>
> <td>是否处于<b><font color="#0000FF">彩</font><font color="#2A2AD4">色</font><font color="#5500AA">失</font><font color="#7F2A7F">衡</font><font color="#AA0055">阶</font><font color="#D42A2A">段</font></b></td>
> </tr>
> <tr>
> <td><code>QTE_triggerable_times</code></td>
> <td><span class="color-number">数值比较</span></td>
> <td>敌人能被连携的最大次数</td>
> </tr>
> <tr>
> <td><code>single_qte</code></td>
> <td><span class="color-none">None比较</span></td>
> <td>是否激发连携并进入连携待应答状态</td>
> </tr>
> <tr>
> <td><code>is_under_anomaly</code></td>
> <td rowspan="7"><span class="color-bool">布尔值比较</span></td>
> <td>敌人是否处于异常状态</td>
> </tr>
> <tr>
> <td><code>is_shock</code></td>
> <td>敌人是否处于<font class="color-shock"><b>感电</b></font>状态</td>
> </tr>
> <tr>
> <td><code>is_burn</code></td>
> <td>敌人是否处于<font class="color-burn"><b>灼烧</b></font>状态</td>
> </tr>
> <tr>
> <td><code>is_assault</code></td>
> <td>敌人是否处于<font class="color-assault"><b>畏缩</b></font>状态</td>
> </tr>
> <tr>
> <td><code>is_frostbite</code></td>
> <td>敌人是否处于<font class="color-frostbite"><b>霜寒</b></font>状态</td>
> </tr>
> <tr>
> <td><code>is_frost_frostbite</code></td>
> <td>敌人是否处于<font class="color-frostfrostbite"><b>烈霜霜寒</b></font>状态</td>
> </tr>
> <tr>
> <td><code>is_corruption</code></td>
> <td>敌人是否处于<font class="color-corruption"><b>侵蚀</b></font>状态</td>
> </tr>
> <tr>
> <td><code>anomaly_pct_0</code></td>
> <td rowspan="7"><span class="color-number">数值比较</span></td>
> <td>敌人当前<font class="color-assault"><b>物理</b></font>属性积蓄百分比</td>
> </tr>
> <tr>
> <td><code>anomaly_pct_1</code></td>
> <td>敌人当前<font class="color-burn"><b>火</b></font>属性积蓄百分比</td>
> </tr>
> <tr>
> <td><code>anomaly_pct_2</code></td>
> <td>敌人当前<font class="color-frostbite"><b>冰</b></font>属性积蓄百分比</td>
> </tr>
> <tr>
> <td><code>anomaly_pct_3</code></td>
> <td>敌人当前<font class="color-shock"><b>电</b></font>属性积蓄百分比</td>
> </tr>
> <tr>
> <td><code>anomaly_pct_4</code></td>
> <td>敌人当前<font class="color-corruption"><b>以太</b></font>属性积蓄百分比</td>
> </tr>
> <tr>
> <td><code>anomaly_pct_5</code></td>
> <td>敌人当前<font class="color-frostfrostbite"><b>烈霜</b></font>属性积蓄百分比</td>
> </tr>
> <tr>
> <td><code>anomaly_pct_6</code></td>
> <td>敌人当前<font class="color-auricink"><b>玄墨</b></font>属性积蓄百分比</td>
> </tr>
> </table>
>
>
> 以上是enemy目前支持的所有检索条件。
>
> <details>
>
> <summary class="details-summary">查看示例</summary>
> <table>
> <tr>
> <td></td>
> <td>示范1</td>
> <td>示范2</td>
> <td>示范3</td>
> </tr>
> <tr>
> <td>APL含义</td>
> <td># 敌人是否处于失衡状态</td>
> <td># 敌人的电属性异常积蓄百分比是否大于等于80%</td>
> <td># 敌人已经被激发了连携技，并且连携技整等待应答</td>
> </tr>
> <tr>
> <td>APL代码</td>
> <td><code>status.enemy:stun==True</code></td>
> <td><code>status.enemy:anomaly_pct_3>=0.8</code></td>
> <td><code>status.enemy:single_qte!=None</code></td>
> </tr>
> </table>
> </details>
>
> enemy部分的参数展示完毕，接下来是角色部分。status类的条件也可以检索角色的属性，只需要在检索目标处填入角色对应的CID即可。
>
> <table class="col-center-1-7">
> <tr>
> <td><b>检索目标</b></td>
> <td><b>分隔符</b></td>
> <td><b>检索内容</b></td>
> <td><b>分隔符</b></td>
> <td><b>嵌套结构键值链</b></td>
> <td><b>比较类型</b></td>
> <td><b>解释</b></td>
> </tr>
> <tr>
> <td rowspan="7"><code>CID<br>角色4位数ID码</code></td>
> <td rowspan="7"><code>:</code></td>
> <td><code>on_field</code></td>
> <td rowspan="7">无分隔符</td>
> <td rowspan="7">无键值链</td>
> <td rowspan="4"><span class="color-bool">布尔值比较</span></td>
> <td>被检索角色是否在前台</td>
> </tr>
> <tr>
> <td><code>char_available</code></td>
> <td>被检索角色是否<abbr title="注：释放连携技或大招、切人CD尚未就绪等无法切出来情况视为角色不可用"><b>可用</b></abbr></td>
> </tr>
> <tr>
> <td><code>quick_assist_available</code></td>
> <td>被检索角色的快速支援是否亮起</td>
> </tr>
> <tr>
> <td><code>assist_waiting_for_anwser</code></td>
> <td>被检索角色是否处于<abbr title="例子：丽娜强化E出手到命中敌人使快速支援亮起这段时间，都属于快速支援即将亮起但还未亮起的状态。由于APL的合轴模式总是会尽快、尽早进行合轴操作，所以很多时候角色会抢在快速支援亮起之前合轴上场。这对类似于耀嘉音这样需要快支才能加上Buff的机制很不友好，而实战中，我们也时常为了让角吃到Buff而“等待快速支援亮起”，所以，当前检索条是为了还原这种情况而设计的。"><b>快速支援即将亮起但还未亮起的状态<sup>1</sup></b></abbr></td>
> </tr>
> <tr>
> <td><code>lasting_node_tag</code></td>
> <td><span class="color-str">字符比较</span></td>
> <td>检索 目标角色连续、重复释放技能的skill_tag，<br>若该角色最近没有连续、重复释放技能，那么就检索最近一次释放的技能</td>
> </tr>
> <tr>
> <td><code>lasting_node_tick</code></td>
> <td rowspan="2"><span class="color-number">数值比较</span></td>
> <td>检索目标角色连续、重复释放技能的持续时间（单位：tick）</td>
> </tr>
> <tr>
> <td><code>repeat_times</code></td>
> <td>检索目标角色连续、重复释放技能的次数</td>
> </tr>
> </table>
>
> ---
>
> ### ▶5.3 属性类条件——attribute
>
> <b>attribute </b>类条件检查的角色的属性，所以其检索目标只有角色一种，填写CID即可。属性类条件不仅可以检索角色的能量、喧响值等属性，也可以检索他们的特殊资源和特殊状态。但是由于不同的角色拥有完全不同的特殊资源系统，所以，不同的CID都有着一些独立的检索内容。在下文中，我会将所有的检索属性分为通用属性、私有属性两大类来进行介绍。
>
> 首先是通用属性，这些属性都是全角色通用的，比如能量、喧响、影画等。
>
> <table class="col-center-1-7">
> <tr>
> <td><b>检索目标</b></td>
> <td><b>分隔符</b></td>
> <td><b>检索内容</b></td>
> <td><b>分隔符</b></td>
> <td><b>嵌套结构键值链</b></td>
> <td><b>比较类型</b></td>
> <td><b>解释</b></td>
> </tr>
> <tr>
> <td rowspan="5"><code>CID<br>角色4位数ID码</code></td>
> <td rowspan="5"><code>:</code></td>
> <td><code>energy</code></td>
> <td rowspan="5">无分隔符</td>
> <td rowspan="5">无键值链</td>
> <td rowspan="3"><span class="color-number">数值比较</span></td>
> <td>检索 目标角色当前的能量</td>
> </tr>
> <tr>
> <td><code>cinema</code></td>
> <td>检索 目标角色当前的影画数值</td>
> </tr>
> <tr>
> <td><code>decibel</code></td>
> <td>检索 目标角色当前的喧响值</td>
> </tr>
> <tr>
> <td><code>special_resource_type</code></td>
> <td><span class="color-str">字符比较</span></td>
> <td>检索 目标角色当前的特殊资源的名称</td>
> </tr>
> <tr>
> <td><code>special_resource</code></td>
> <td><span class="color-number">数值比较</span>/<span class="color-bool">布尔值比较</span></td>
> <td>检索 目标角色当前的特殊资源的数值</td>
> </tr>
> </table>
>
> 对于最后的两个属性：special_resource_type和special_resource，这里需要进行额外说明。它们检索的是角色的特殊资源，前者返回特殊资源的名称，后者返回特殊资源的数值。不过角色可能拥有多个特殊资源，所以special_resource_type和special_resource只会返回其中最重要的一对。
>
> 当然，special_resource_type的使用频率相当低，甚至是不会被用到的，因为我们一般不需要判断某个角色是否拥有某个种类的特殊资源（比如在扳机相关的APL中，判断扳机的特殊资源是不是叫“决意值”毫无意义）。一般来说，我们只使用special_resource来进行特殊资源的判定。
>
> 这两个属性的具体情况如下：
>
> <table class="col-center-1-7">
> <tr>
> <td><b>CID</b></td>
> <td><b>角色姓名</b></td>
> <td><code><b>special_resource_type</b></code><br>（str）</td>
> <td><code><b>special_resource</b></code><br>（int / bool / float）</td>
> <td><b>数值类型</b></td>
> <td><b>取值范围</b></td>
> </tr>
> <tr>
> <td>1361</td>
> <td>扳机</td>
> <td>决意值</td>
> <td>决意值数值</td>
> <td class="color-number">float</td>
> <td>（0画）0~100<br>（1画及以上）0~125</td>
> </tr>
> <tr>
> <td>1331</td>
> <td>薇薇安</td>
> <td>护羽</td>
> <td>护羽数值</td>
> <td class="color-number">int</td>
> <td>0~6</td>
> </tr>
> <tr>
> <td>1221</td>
> <td>柳</td>
> <td colspan="3">由于柳没有特殊资源（架势状态通过<code>special_state</code>属性检索），<br>所以柳的<code>special_resource</code>和<code>special_resource_type</code>返回的是<code>None</code></td>
> <td>None</td>
> </tr>
> <tr>
> <td>1311</td>
> <td>耀嘉音</td>
> <td>咏叹华彩</td>
> <td>咏叹华彩状态</td>
> <td class="color-bool">bool</td>
> <td>True / False</td>
> </tr>
> <tr>
> <td>1191</td>
> <td>艾莲</td>
> <td>急冻充能</td>
> <td>急冻充能点数</td>
> <td class="color-number"; rowspan="5">int</td>
> <td>0~6</td>
> </tr>
> <tr>
> <td>1091</td>
> <td>雅</td>
> <td>落霜</td>
> <td>落霜点数</td>
> <td>0~6</td>
> </tr>
> <tr>
> <td>1041</td>
> <td>11号</td>
> <td>火力镇压</td>
> <td>火力镇压层数</td>
> <td>0~8</td>
> </tr>
> <tr>
> <td>1241</td>
> <td>朱鸢</td>
> <td>强化霰弹</td>
> <td>强化霰弹层数</td>
> <td>0~9</td>
> </tr>
> <tr>
> <td>1131</td>
> <td>苍角</td>
> <td>涡流</td>
> <td>涡流层数</td>
> <td>0~3</td>
> </tr>
> <tr>
> <td>1301</td>
> <td>简</td>
> <td>狂热心流</td>
> <td>狂热心流值</td>
> <td class="color-number"; rowspan="5">float</td>
> <td>0~100</td>
> </tr>
> <tr>
> <td>1161</td>
> <td>莱特</td>
> <td>士气</td>
> <td>士气值</td>
> <td>0~100</td>
> </tr>
> <tr>
> <td>1300</td>
> <td>青衣</td>
> <td>闪络电压</td>
> <td>闪络电压值</td>
> <td>0~100</td>
> </tr>
> <tr>
> <td>1381</td>
> <td>零号·安比</td>
> <td>银星层数</td>
> <td>银星层数</td>
> <td>0~3</td>
> </tr>
> <tr>
> <td>1371</td>
> <td>仪玄</td>
> <td>闪能</td>
> <td>闪能点数</td>
> <td>0~120</td>
> </tr>
> <tr>
> <td>0000</td>
> <td></td>
> <td></td>
> <td></td>
> <td></td>
> <td></td>
> </tr>
> </table>
>
> 介绍完通用属性，接下来是比较复杂的special_state属性，不同角色special_state的检索结果是不同的，所以我们按照不同的CID来介绍。
>
> <table class="col-center-1-7">
> <tr>
> <td><b>检索目标</b></td>
> <td><b>分隔符</b></td>
> <td><b>检索内容</b></td>
> <td><b>分隔符</b></td>
> <td><b>嵌套结构键值链</b></td>
> <td><b>比较类型</b></td>
> <td><b>解释</b></td>
> </tr>
> <tr>
> <td rowspan="1"; class="color-3">1361</br>（扳机）</td>
> <td rowspan="34"><code>:</code></td>
> <td rowspan="34"><code>special_state</code></td>
> <td rowspan="34">→</td>
> <td class="color-3">狙击姿态</td>
> <td class="color-3"><span class="color-bool">布尔值比较</span></td>
> <td class="color-3">检索 扳机当前是否处于狙击姿态</td>
> </tr>
> <tr>
> <td rowspan="4" class="color-4">1331<br>（薇薇安）</td>
> <td class="color-4">护羽数量</td>
> <td class="color-4"; rowspan=2><span class="color-number">数值比较</span></td>
> <td class="color-4">检索 薇薇安当前的护羽数量</td>
> </tr>
> <tr>
> <td class="color-4">飞羽数量</td>
> <td class="color-4">检索 薇薇安当前的飞羽数量</td>
> </tr>
> <tr>
> <td class="color-4">裙裾浮游</td>
> <td class="color-4"; rowspan=2><span class="color-bool">布尔值比较</span></td>
> <td class="color-4">检索 薇薇安当前是否处于裙裾浮游状态</td>
> </tr>
> <tr>
> <td class="color-4">淑女礼仪</td>
> <td class="color-4">检索 薇薇安当前是否处于淑女礼仪状态</td>
> </tr>
> <tr>
> <td rowspan="2"; class="color-3">1221<br>（柳）</td>
> <td class="color-3">当前架势</td>
> <td class="color-3"; rowspan=2><font class="color-bool">布尔值比较</font></td>
> <td class="color-3">检索 柳的当前架势，True为上弦，False为下弦</td>
> </tr>
> <tr>
> <td class="color-3">森罗万象状态</td>
> <td class="color-3">检索 柳当前的森罗万象状态的激活情况</td>
> </tr>
> <tr>
> <td rowspan="1"; class="color-4">1311<br>（耀嘉音）</td>
> <td class="color-4">咏叹华彩</td>
> <td class="color-4"><span class="color-bool">布尔值比较</span></td>
> <td class="color-4">检索 耀嘉音当前是否处于咏叹华彩状态</td>
> </tr>
> <tr>
> <td rowspan="1"; class="color-2">1191<br>（艾莲）</td>
> <td class="color-2"; colspan=3>该角色没有可以被检索的特殊状态</td>
> </tr>
> <tr>
> <td rowspan="1"; class="color-5">1091<br>（雅）</td>
> <td class="color-5"; colspan=3>该角色没有可以被检索的特殊状态</td>
> </tr>
> <tr>
> <td rowspan="1"; class="color-1">1041<br>（11号）</td>
> <td class="color-1"; colspan=3>该角色没有可以被检索的特殊状态</td>
> </tr>
> <tr>
> <td rowspan="1"; class="color-4">1241<br>（朱鸢）</td>
> <td class="color-4"; colspan=3>该角色没有可以被检索的特殊状态</td>
> </tr>
> <tr>
> <td rowspan="1"; class="color-2">1131<br>（苍角）</td>
> <td class="color-2"; colspan=3>该角色没有可以被检索的特殊状态</td>
> </tr>
> <tr>
> <td rowspan="3"; class="color-0">1301<br>（简）</td>
> <td class="color-0">狂热心流</td>
> <td class="color-0"><font class="color-number">数值比较</font></td>
> <td class="color-0">检索 简当前的狂热心流数值</td>
> </tr>
> <tr>
> <td class="color-0">狂热状态</td>
> <td class="color-0"><font class="color-bool">布尔值比较</font></td>
> <td class="color-0">检索 简当前是否处于狂热状态</td>
> </tr>
> <tr>
> <td class="color-0">萨霍夫跳剩余次数</td>
> <td class="color-0"><font class="color-number">数值比较</font></td>
> <td class="color-0">检索 简当前的萨霍夫跳的剩余可用次数</td>
> </tr>
> <tr>
> <td rowspan="1"; class="color-1">1161<br>（莱特）</td>
> <td class="color-1">士气</td>
> <td class="color-1"; rowspan=1><font class="color-number">数值比较</font></td>
> <td class="color-1">检索 莱特当前的士气值</td>
> </tr>
> <tr>
> <td rowspan="3"; class="color-3">1300<br>（青衣）</td>
> <td class="color-3">闪络电压</td>
> <td class="color-3"; rowspan=2><font class="color-number">数值比较</font></td>
> <td class="color-3">检索 青衣当前的闪络电压值</td>
> </tr>
> <tr>
> <td class="color-3">醉话月云转可用次数</td>
> <td class="color-3">检索 青衣当前的<abbr title="青衣的重击分成5次突刺攻击和1次终结一击，这里检索的就是重击的突刺攻击的剩余次数，用于判断青衣是否要打完全部重击，或者直接结束收招打终结一击"><b>醉花月云转突刺攻击</b></abbr>的剩余可用次数</td>
> </tr>
> <tr>
> <td class="color-3">闪络状态</td>
> <td class="color-3"; rowspan=1><font class="color-bool">布尔值比较</font></td>
> <td class="color-3">检索 青衣当前是否处于闪络状态</td>
> </tr>
> <tr>
> <td rowspan="10"; class="color-3">1381<br>（零号·安比）</td>
> <td class="color-3">白雷<font color="gray">(内部功能)</font></td>
> <td class="color-3"; rowspan=6><font class="color-bool">布尔值比较</font></td>
> <td class="color-3">检索 大安比的<abbr title="这是内置功能，基本没有被外部调用的可能性。大安比的白雷触发行为是比E技能命中晚1帧的，在ZSim内部，符合触发条件的E技能会打开白雷触发器，然后大安比的特殊资源模块会根据白雷触发器的状态，抛出白雷技能，白雷技能结算时，会关闭白雷触发器。所以白雷触发器为True时，就是E技能命中但是白雷尚未触发的时间点（其实这个状态值会持续1~2帧）"><b>白雷触发器</b></abbr>的开合状态</td>
> </tr>
> <tr>
> <td class="color-3">雷殛<font color="gray">(内部功能)</font></td>
> <td class="color-3">检索 大安比的<abbr title="这是内置功能，基本没有被外部调用的可能性。和白雷触发器一样，在白雷连续命中3次的时，第3个白雷在结算时会打开雷殛触发器，而特殊资源模块会根据雷殛触发器的状态抛出雷殛，雷殛在结算时会关闭触发器终止触发信号。"><b>雷殛触发器</b></abbr>的开合状态</td>
> </tr>
> <tr>
> <td class="color-3">6画状态<font color="gray">(内部功能)</font></td>
> <td class="color-3">检索 大安比的<abbr title="这是内置功能，基本没有被外部调用的可能性。连续6次的白雷会开启6画触发器，特殊资源模块会根据触发器状态抛出电磁涡流，电磁涡流结算时，关闭6画触发器。"><b>6画触发器</b></abbr>的开合状态</td>
> </tr>
> <tr>
> <td class="color-3">1画状态<font color="gray">(内部功能)</font></td>
> <td class="color-3">检索 大安比的<abbr title="这是内置功能，基本没有被外部调用的可能性。1画状态下，强化E首次命中时，1画触发器打开，3+1结束后，1画触发器关闭。"><b>1画触发器</b></abbr>的开合状态</td>
> </tr>
> <tr>
> <td class="color-3">E连击</td>
> <td class="color-3">检索 大安比是否处于连续释放E技能的状态</td>
> </tr>
> <tr>
> <td class="color-3">满层</td>
> <td class="color-3">检索 大安比的银星标记是否叠满</td>
> </tr>
> <tr>
> <td class="color-3">白雷连击次数</td>
> <td class="color-3"; rowspan=4><font class="color-number">数值比较</font></td>
> <td class="color-3">检索 大安比的白雷连击次数</td>
> </tr>
> <tr>
> <td class="color-3">2画_电鸣</td>
> <td class="color-3">检索 大安比2画的电鸣的剩余可用次数</td>
> </tr>
> <tr>
> <td class="color-3">6画_白雷次数</td>
> <td class="color-3">检索 大安比6画的白雷计数器</td>
> </tr>
> <tr>
> <td class="color-3">1画_白雷次数</td>
> <td class="color-3">检索 大安比1画的白雷计数器</td>
> </tr>
> <tr>
> <td rowspan="4"; class="color-4">1307<br>（仪玄）</td>
> <td class="color-4">术法值</td>
> <td rowspan="4"; class="color-4"><font class="color-number">数值比较</font></td>
> <td class="color-4">检索 仪玄当前的术法值</td>
> </tr>
> <tr>
> <td class="color-4">玄墨值</td>
> <td class="color-4">检索 仪玄当前的玄墨值</td>
> </tr>
> <tr>
> <td class="color-4">聚墨点数</td>
> <td class="color-4">检索 仪玄当前的聚墨点数</td>
> </tr>
> <tr>
> <td class="color-4">调息层数</td>
> <td class="color-4">检索 仪玄当前的调息层数</td>
> </tr>
> </table>
>
> 至此，所有ZSim当前支持角色的special_state相关的参数以及键值链就已经全部列出
>
> 这部分APL的书写示范如下：
>
> <details>
> <summary class="details-summary">查看示例</summary>
> <table>
> <tr>
> <td></td>
> <td>示范1</td>
> <td>示范2</td>
> <td>示范3</td>
> </tr>
> <tr>
> <td>APL含义</td>
> <td># 青衣的醉话月云转突刺攻击剩余次数大于1次</td>
> <td># 简不处于狂热状态下</td>
> <td># 大安比正处于E连击状态下</td>
> </tr>
> <tr>
> <td>APL代码</td>
> <td><code>attribute.1300:special_state→醉花月云转可用次数>1</code></td>
> <td><code>attribute.1301:special_state→狂热状态==False</code></td>
> <td><code>attribute.1381:special_state→E连击==True</code></td>
> </tr>
> </table>
> </details>
>
> ---
>
> ### ▶5.4 增减益效果类条件——buff
>
> APL还支持 <b>buff </b>类条件，这类条件只有3个功能，针对Buff存在状态、 持续时间、当前层数的检查，语法如下：
>
> <table class="col-center-1-7">
> <tr>
> <td><b>检索目标</b></td>
> <td><b>分隔符</b></td>
> <td><b>检索内容</b></td>
> <td><b>分隔符</b></td>
> <td><b>嵌套结构键值链</b></td>
> <td><b>比较类型</b></td>
> <td><b>解释</b></td>
> </tr>
> <tr>
> <td rowspan="3">CID<br>enemy</td>
> <td rowspan="3"><code>:</code></td>
> <td ><code>exist</code></td>
> <td rowspan="3">→</td>
> <td rowspan="3">buff名<br><font color=orange>xxx</font></td>
> <td rowspan="1"><span class="color-bool">布尔值比较</span></td>
> <td>检索 Buff（<font color=orange>xxx</font>）是否存在于角色（CID）或enemy身上</td>
> </tr>
> <tr>
> <td ><code>duration</code></td>
> <td rowspan="2"><span class="color-number">数值比较</span></td>
> <td>检索 角色（CID）或enemy身上的Buff（<font color=orange>xxx</font>）的持续时间</td>
> </tr>
> <tr>
> <td ><code>count</code></td>
> <td>检索 角色（CID）或enemy身上 Buff（<font color=orange>xxx</font>）的层数</td>
> </tr>
> </table>
>
> <b>buff </b>类条件最重要的是确定buff名，考虑到ZSim中的Buff数量超过1000，在这里我就不一一展开，你可以前往data下的buff数据库（激活判断.csv、触发判断.csv、buff_effect.csv）进行查看。
>
> 这部分APL的书写规范如下：
>
> <details>
> <summary class="details-summary">查看示例</summary>
> <table>
> <tr>
> <td></td>
> <td>示范1</td>
> <td>示范2</td>
> </tr>
> <tr>
> <td>APL含义</td>
> <td># 雅身上存在丽娜的穿透率Buff</td>
> <td># 柳身上存在耀嘉音的攻击力Buff</td>
> </tr>
> <tr>
> <td>APL代码</td>
> <td>buff.1091:exist→Buff-角色-丽娜-核心被动-穿透率==True</td>
> <td>buff.1221:Buff-角色-耀佳音-核心被动-攻击力==True</td>
> </tr>
> </table>
> </details>
>
> ---
>
> ### ▶5.5 特殊类条件——special
>
> 当前，special类条件还处于开发阶段，表现并不稳定，请谨慎使用。
> <table class="col-center-1-7">
> <tr>
> <td><b>检索目标</b></td>
> <td><b>分隔符</b></td>
> <td><b>检索内容</b></td>
> <td><b>嵌套结构键值链</b></td>
> <td><b>比较类型</b></td>
> <td><b>解释</b></td>
> </tr>
> <tr>
> <td rowspan="2">无要求<br>一般写preload_data</td>
> <td rowspan="2"><code>:</code></td>
> <td ><code>operating_char</code></td>
> <td rowspan="2">无</td>
> <td rowspan="1"><span class="color-number">数值比较</span></td>
> <td>检索当前正在进行主动操作的角色的CID<br>（扳机协同攻击这种并非由玩家直接指令引发的动作就不属于主动操作，同时，若当前tick无角色主动操作，APL会主动获取当前处于前台的角色的CID）</td>
> </tr>
> <tr>
> <td ><code>is_attacking</code></td>
> <td rowspan="1"><span class="color-bool">布尔值比较</span></td>
> <td>检索 当前tick的战斗中，是否存在激活的进攻事件</td>
> </tr>
> </table>
>
> 示范：
>
> \# 当前当前操作角色的是柳
>
> special.preload_data:operating_char==1221

---

## 6、应用示范及讲解

 接下来是APL代码的展示与讲解环节。我选择了一段 青衣、丽娜、雅队伍的爆发期APL来进行展示。注意，为了方便大家理解APL的运行逻辑以及优化流程，这套展示给大家看的APL代码并非是最优解，有着较多的可优化空间。

```python
#失衡期间丽娜要满覆盖buff
1211|action+=|1211_NA_1|status.enemy:stun==True|!buff.1091:exist→Buff-角色-丽娜-核心被动-穿透率==True|status.enemy:QTE_activation_available==False
  
#满豆自动放满蓄力普攻
1091|action+=|1091_SNA_3|attribute.1091:special_resource==6|buff.1091:exist→Buff-角色-丽娜-核心被动-穿透率==True|status.enemy:stun==True
  
#能量不够时应优先大招
1091|action+=|1091_Q|attribute.1091:special_resource>3|attribute.1091:decibel==3000|status.enemy:stun==True|attribute.1091:energy<40
  
#豆子相差很远时，也优先开大
1091|action+=|1091_Q|attribute.1091:special_resource<4|attribute.1091:decibel==3000|status.enemy:stun==True
  
#有能量、有大时，根据豆子数量判断大招如何释放。
1091|action+=|1091_E_EX_A_1|status.enemy:stun==True|attribute.1091:special_resource<6|attribute.1091:special_resource>4|attribute.1091:decibel==3000
1091|action+=|1091_Q|status.enemy:stun==True|attribute.1091:special_resource<3|attribute.1091:decibel==3000
  
#泄能逻辑
1091|action+=|1091_E_EX_B_1|status.enemy:stun==True|attribute.1091:energy>=40|attribute.1091:special_resource<6|action.1091:strict_linked_after==1091_E_EX_A_2
1091|action+=|1091_E_EX_A_1|status.enemy:stun==True|attribute.1091:energy>=40|attribute.1091:special_resource<6
  
#剩余情况都是后置开大
1091|action+=|1091_Q|attribute.1091:special_resource<4|attribute.1091:decibel==3000|status.enemy:stun==True
  
```

接下来，我将针对上面展示的这部分APL代码进行逐行讲解，

在逐行讲解的过程中，我将为大家详细讲解APL的具体作用和逻辑，以及多条APL相互组合时的效果。

> ```python
> #失衡期间丽娜要满覆盖buff
> 1211|action+=|1211_NA_1|status.enemy:stun==True|!buff.1091:exist→Buff-角色-丽娜-核心被动-穿透率==True
> ```
>
> 在失衡期，如果发现丽娜Buff断了，那么就要切出丽娜来A一下，续上穿透率Buff。这里不用E的原因是为了省时间，在实战中，我们也能在竞速视频中观察到选手使用丽娜的A1来快速续Buff的操作。

> ```python
> #满豆自动放满蓄力普攻
> 1091|action+=|1091_SNA_3|attribute.1091:special_resource==6|buff.1091:exist→Buff-角色-丽娜-核心被动-穿透率==True|status.enemy:stun==True
> ```
>
> 在失衡期，雅在拥有6个豆子时，只会在身上有丽娜穿透率Buff的时候释放满蓄力普攻。换言之，如果雅的豆子满了，但是身上没有Buff，那么本行APL的判定就不通过，是不会释放满蓄力普攻的。这一行APL是为了防止雅打出低质量的满蓄普攻。

> ```python
> #能量不够时应优先大招
> 1091|action+=|1091_Q|attribute.1091:special_resource>3|attribute.1091:decibel==3000|status.enemy:stun==True|attribute.1091:energy<40
> ```
>
> 在失衡期，雅大招就绪但能量不够时，就会释放大招，无论身上有没有丽娜穿透率Buff。但是请注意，单独来看这是一条有问题的APL。因为该条APL会导致雅在满豆、满喧响的情况下优先开大。想要修复这一手法逻辑，只需要在这一行APL的末尾加上一个条件即可：
>
> ```python
> ……|attribute.1091:special_resource<6
> ```
>
> 只要将豆子的数量锁定住，那么这一条APL就能正常发挥作用。
>
> 但是有趣的是，如果将以上3条APL同时激活，并且按照文中展示的顺序进行排列，那么即使是有缺陷的本行APL，也不会导致出错。
>
>> <details>
>>     <summary style="color: gray">展开说明</summary>
>>     <p style="text-indent: 2em; color: gray">由于APL的执行顺序是从上到下，所以，在执行到这一行之前，前两行是一定没有通过的。前面我们介绍过，导致本行APL出错的条件集为：满豆且满喧响。那么这种场景，会在第二行APL被拦下来。上面展示的第二行APL，就是让雅在有穿透率Buff的时候，优先泄豆。</br></p>
>>     <p style="text-indent: 2em; color: gray">有的读者可能又注意到了新的问题。“那如果身上恰好没有Buff，且满豆，那APL的执行不就漏到第三行了吗？”</br></p>
>>     <p style="text-indent: 2em; color: gray">放心，这个情况也是不会出现的。因为在失衡期，身上没有Buff的情况会被第一行APL拦下来。</br></p>
>>     <p style="text-indent: 2em; color: gray">总之，如果APL的运行来到了第三行，那么就说明当前起码是：有穿透率Buff且不满豆的状态，也就是说，我们补写的那个条件判定，在第三行的位置上，是永远不会起到作用的。</br></p>
>>     <p style="text-indent: 2em; color: gray">可见，APL的优先级思维要求大家以全新的视角来拆分、看待自己的游戏逻辑。</p>
>> </details>
>>

> ```python
> #豆子相差很远时，也优先开大
> 1091|action+=|1091_Q|attribute.1091:special_resource<4|attribute.1091:decibel==3000|status.enemy:stun==True
> ```
>
> 和上一句的大招APL相比，这一句改变了豆子的判定，并且取消了能量的判定。只有满足以下条件（可以简单概括为：要么豆子数量不对，要么能量值不对），APL才的执行才会来到第四行（不满足的条件为 <span style="color: orange">橙色）：
>
> <b>情况1：</b>满喧响（默认） | 豆子∈\(3, 6\]| <span style="color: orange">能量足够
>
> <b>情况2：</b>满喧响（默认） | <span style="color: orange">豆子∈[0, 3] | 能量不够
>
> <b>情况3：</b>满喧响（默认） | <span style="color: orange">豆子∈[0, 3] | <span style="color: orange">能量足够
>
> 而本条APL针对的恰好就是 <b>情况2 </b>，即在有没能量，且大招不会导致豆子溢出时开大。

> ```python
> #泄能逻辑
> 1091|action+=|1091_E_EX_A_1|status.enemy:stun==True|attribute.1091:energy>=40|attribute.1091:special_resource<6
> ```
>
> 这里展示的APL是雅在失衡期的泄能逻辑。如果你全局检查目前已经展示的5行APL，你就不难发现本行APL中藏着一个无效条件——能量判定。从上面的三种情况的列举可以看出，能够进入到这一行的APL，均是能量足够的情况。所以能量判定在这一行是无效的。
>
> 这也意味着，这一行APL的作用，就是“无脑泄蓝”，哪怕此时喧响值足够，也是优先打强化E。<span style="color: gray">（很明显，这个逻辑是不对的，在实战中我们面对豆子不满、且有能量、有大的情况，往往会先进行豆子判断。如果开大豆子不溢出，那就优先开大，如果开大豆子溢出，那就优先打E。）
>
> 根据上述推理，这一行的APL实际上可以优化为以下两行来执行。
>
> ```python
> 1091|action+=|1091_E_EX_A_1|status.enemy:stun==True|attribute.1091:special_resource<6|attribute.1091:special_resource>4
> 1091|action+=|1091_Q|status.enemy:stun==True|attribute.1091:special_resource<3
> ```
>
> 这两行APL如果调换先后顺序，实际上起到的效果是完全相同的。这也是APL的一个核心特点：位于分类讨论末端的几种情况的APL先后顺序不影响实际效果，因为它们本质上是同优先级的APL。

## 7、结尾

通过本文档，我们详细介绍了ZSim中APL模块的设计原理、语法规则以及实际应用示例。

APL作为ZSim的核心功能之一，能够帮助玩家精确模拟角色的输出逻辑，优化战斗策略。希望本文档能够为开发者和使用者提供清晰的指导，帮助大家更好地理解和使用APL功能。

#### 后续计划

- 编写一个可视化的修改APL代码的前端工具
- 开发APL语法检查器
- 支持“或”逻辑：当前版本的APL仅支持“与”逻辑，未来我们将优先开发“或”逻辑的支持，以简化复杂条件的编写。
- 扩展条件类型：我们计划增加更多的条件类型，以支持更复杂的战斗场景和角色机制。
- 优化性能：进一步提升APL的解析和执行效率，确保在大规模模拟中的稳定性。
  
#### 反馈与支持

如果您在使用过程中遇到任何问题，或有任何建议和反馈，欢迎通过以下方式联系我们：

邮箱：<1012399286@qq.com>

感谢您对ZSim的支持，我们将持续改进和优化，为您提供更好的模拟体验。
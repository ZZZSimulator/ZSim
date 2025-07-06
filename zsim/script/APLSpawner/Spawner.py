import dash
from dash import Dash, dcc, html, Output, Input
import dash_bootstrap_components as dbc
import pandas as pd
from zsim.define import CHARACTER_DATA_PATH

# 初始化角色数据
char_data = pd.read_csv(CHARACTER_DATA_PATH)
full_char_name_list = char_data["name"].tolist()
full_char_cid_list = char_data["CID"].tolist()
full_char_dict = {
    name: cid for name, cid in zip(full_char_name_list, full_char_cid_list)
}


class Spawner:
    def __init__(self):
        self.full_char_dict = full_char_dict


spawner_data = Spawner()
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.layout = html.Div(
    [
        dcc.Tabs(
            id="tbas-container",
            value="char-select-tab",
            children=[
                dcc.Tab(
                    label="角色选择",
                    value="char-select-tab",
                    children=[
                        dbc.Row(
                            [
                                dbc.Col(
                                    dcc.Dropdown(
                                        id="char-select-box-1",
                                        options=[
                                            {"label": t[0], "value": t[1]}
                                            for t in spawner_data.full_char_dict.items()
                                        ],
                                    ),
                                    md=4,  # 每列占4格（Bootstrap共12格）
                                ),
                                dbc.Col(
                                    dcc.Dropdown(
                                        id="char-select-box-2",
                                        options=[
                                            {"label": t[0], "value": t[1]}
                                            for t in spawner_data.full_char_dict.items()
                                        ],
                                    ),
                                    md=4,  # 每列占4格（Bootstrap共12格）
                                ),
                                dbc.Col(
                                    dcc.Dropdown(
                                        id="char-select-box-3",
                                        options=[
                                            {"label": t[0], "value": t[1]}
                                            for t in spawner_data.full_char_dict.items()
                                        ],
                                    ),
                                    md=4,
                                ),
                            ]
                        ),
                        # 第一行 三个角色选择框结束，第二行开始
                        dbc.Button(),
                    ],
                )
            ],
        )
    ]
)


@app.callback(
    [
        Output(component_id="char-select-box-1", component_property="options"),
        Output(component_id="char-select-box-2", component_property="options"),
        Output(component_id="char-select-box-3", component_property="options"),
    ],
    [
        Input(component_id="char-select-box-1", component_property="value"),
        Input(component_id="char-select-box-2", component_property="value"),
        Input(component_id="char-select-box-3", component_property="value"),
    ],
    prevent_initial_call=True,
)
def update_dropdown(char_1, char_2, char_3):
    """
    回调1：角色选择界面的下拉菜单回调。
    根据在下拉菜单中选择的角色，修改其他菜单的内容。
    """
    """第一步：锁定触发会调函数的源头"""
    ctx = dash.callback_context
    """callback_context解释：
    dash.callback_context输出的内容如下，根据AI的介绍，它输出的应该是JSON格式：
        {
            "triggered": [
                    {
                    "prop_id": "char-select-box_1.value",  // 触发源组件ID及属性
                    "value": "1001",                       // 触发时的属性值
                    "triggered": true                       // 是否实际触发
                    },
                    {
                    "prop_id": ".",                        // 其他可能存在的非主动触发项
                    "value": null,
                    "triggered": false
                    }]
        }
        所以才需要下面代码的格式整理，最终获取triggered_id
    """
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate
    selected = {val for val in [char_1, char_2, char_3] if val is not None}
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]

    filtered_options = []
    for name, cid in spawner_data.full_char_dict.items():
        if cid not in selected:
            filtered_options.append({"label": name, "value": cid})
        else:
            filtered_options.append(
                {"label": f"{name} (已选)", "value": cid, "disabled": True}
            )
    # 仅更新触发源的下拉框
    if triggered_id == "char-select-box-1":
        return filtered_options, dash.no_update, dash.no_update
    elif triggered_id == "char-select-box-2":
        return dash.no_update, filtered_options, dash.no_update
    elif triggered_id == "char-select-box-3":
        return dash.no_update, dash.no_update, filtered_options
    else:
        raise ValueError("触发源ID错误！")


@app.callback()
def select_char_complete():
    """
    回调2：锁定选择按钮回调函数，
    主要是判定角色是否完成选择，如果完成选择，那么就开放新的标签页。
    """
    pass


if __name__ == "__main__":
    app.run_server(debug=True)

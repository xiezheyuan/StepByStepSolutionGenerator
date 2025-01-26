import rsa
import json
import base64
import requests
import streamlit as st
import os

# 填写你自己的私钥和公钥（注意：这里要手动填写）
private_key_pem = b"""
-----BEGIN RSA PRIVATE KEY-----
MIIBPQIBAAJBALVpNcw7JAx4r0d8e9YkLjQ5AcaeZAdvo6PEZN5ZdwFI6ccQCafj
x+zCK/tzuLTuRbZUqCQoSVawLoFl9xtpxoMCAwEAAQJAKus+SBhB2hV/WolP/wTG
TaKjEeuNPNkjvO4M8zH1K0gFb0hFQiQG25Nd9V8beEnDdB0pmdPSniFznA+vdQnP
SQIjANmKSL1NHrzkcWRs1C7rcZw6/lDUjnqAipOU377tM1WUit8CHwDVe75yUbwG
ZWAJ7FR/oyphrPByU0tJYIiHzCoynN0CIkuiervmjmNagdpKxFMz5SJOmJF99bO9
8XByeICndAuzQ70CHwCbKKTyUZVm0KdMjwea/OwAscDQVtmRKygQCsNgpcECIwC6
QgKnXdYMFk07dnEpINcWdDp/ch7RBiODB9EUHeUN1WRM
-----END RSA PRIVATE KEY-----
"""
public_key_pem = b"""
-----BEGIN RSA PUBLIC KEY-----
MEgCQQC1aTXMOyQMeK9HfHvWJC40OQHGnmQHb6OjxGTeWXcBSOnHEAmn48fswiv7
c7i07kW2VKgkKElWsC6BZfcbacaDAgMBAAE=
-----END RSA PUBLIC KEY-----
"""

# 加载私钥和公钥
private_key = rsa.PrivateKey.load_pkcs1(private_key_pem)
public_key = rsa.PublicKey.load_pkcs1(public_key_pem)

config_file = "config.json"

# 加密解密函数
def encrypt_data(data, public_key):
    return rsa.encrypt(data.encode(), public_key)

def decrypt_data(encrypted_data, private_key):
    return rsa.decrypt(encrypted_data, private_key).decode()

# 配置文件处理
def load_config():
    if os.path.exists(config_file):
        try:
            with open(config_file, "r") as f:
                config = json.load(f)
            encrypted_api_key = base64.b64decode(config['api_key'])
            config['api_key'] = decrypt_data(encrypted_api_key, private_key)
            return config
        except Exception as e:
            st.error(f"加载配置出错: {e}")
            return None
    return None

def save_config(base_url, engine, api_key):
    try:
        encrypted_api_key = base64.b64encode(encrypt_data(api_key, public_key)).decode()
        config = {"base_url": base_url, "engine": engine, "api_key": encrypted_api_key}
        with open(config_file, "w") as f:
            json.dump(config, f, indent=4)
        st.success("配置保存成功！")
    except Exception as e:
        st.error(f"保存配置失败: {e}")

prompt = """
将以下编程竞赛题目的解析转换为 JSON 格式，用于分步解析。
每个步骤作为 JSON 对象中的一个条目，每个条目应包括步骤编号和内容描述。如果内容描述是其他语言的，尝试翻译为简体中文。

请参考以下提供的原始解析和相应的 JSON 表达示例：

原始解析示例：
\"""
It can be seen that this is a dynamic programming problem. Let's consider how to approach it with DP. Let f(i, j) represent the maximum profit when considering the i-th item with a total weight of j. The transition is straightforward, but a rolling array should be used to optimize space complexity.\"""

JSON 表达示例：
[
  {{"step": "步骤 1", "content": "可以看出这是一个动态规划问题，不妨思考一下如何dp；"}},
  {{"step": "步骤 2", "content": "设f(i,j)表示考虑到第i个物品，总重量为j的最大收益和，转移是容易的；"}},
  {{"step": "步骤 3", "content": "尝试利用滚动数组来优化空间复杂度。"}}
]

请将以下原始解析转化为 JSON 表达：
===
{text}
===
"""

# 修改后的API请求函数
def get_custom_api_tips(base_url, api_key, params, text):
    headers = {'Authorization': f'Bearer {api_key}'}
    payload = {
        "model": params['engine'],
        "messages": [{"role": "user", "content": text}],
        "max_tokens": params['max_tokens'],  # 新增参数
        "temperature": params['temperature']  # 新增参数
    }
    try:
        response = requests.post(
            f"{base_url}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30  # 添加超时处理
        )
        if response.status_code == 200:
            result = response.json()["choices"][0]["message"]["content"]
            result = result.strip().rstrip()
            if result.startswith("```json"):
                result = result[len("```json"):]
            if result.startswith("```"):
                result = result[len("```"):]
            if result.endswith("```"):
                result = result[:-len("```")]
            print(result)
            result = json.loads(result)
            content = []
            print(result)
            for i in result:
                content.append(f"### {i['step']}\n\n{i['content']}")
            return content
        else:
            st.error(f"API请求失败: {response.text}")
    except Exception as e:
        st.error(f"请求异常: {str(e)}")
    return []

# Streamlit界面调整
# config = load_config()

with st.sidebar:
    st.header("🛠️ 配置中心")

    # ===== 配置文件上传 =====
    uploaded_config = st.file_uploader("上传配置文件", type=["json"],
                                     help="支持包含加密API密钥的配置文件")

    # ===== 会话状态初始化 =====
    if 'llm_config' not in st.session_state:
        st.session_state.llm_config = {
            'base_url': 'https://api.openai.com',
            'engine': 'gpt-3.5-turbo',
            'api_key': '',          # 内存存储真实密钥
            'max_tokens': 5000,
            'temperature': 0.7,
            'prompt': prompt       # 新增prompt存储
        }

    # ===== 解析上传的配置 =====
    if uploaded_config:
        try:
            config = json.load(uploaded_config)

            # 解密并更新配置（不显示敏感信息）
            st.session_state.llm_config.update({
                'base_url': config.get('base_url', st.session_state.llm_config['base_url']),
                'engine': config.get('engine', st.session_state.llm_config['engine']),
                'api_key': decrypt_data(base64.b64decode(config['api_key']), private_key),
                'max_tokens': config.get('max_tokens', 5000),
                'temperature': config.get('temperature', 0.7),
                'prompt': config.get('prompt', prompt)  # 新增prompt加载
            })
            st.success("配置已安全加载")
        except Exception as e:
            st.error(f"配置加载失败: {str(e)}")

    # ===== 配置输入组件 =====
    base_url = st.text_input('API 基地址',
                           value=st.session_state.llm_config['base_url'],
                           key='base_url_input')

    engine = st.text_input('模型名称',
                         value=st.session_state.llm_config['engine'],
                         key='engine_input')

    # 新增参数组件
    max_tokens = st.number_input('最大Token数',
                               min_value=100, max_value=400000,
                               value=st.session_state.llm_config['max_tokens'],
                               key='max_tokens_input')

    temperature = st.slider('温度系数',
                          min_value=0.0, max_value=2.0, step=0.1,
                          value=st.session_state.llm_config['temperature'],
                          key='temperature_input')

    # ===== Prompt模板编辑 =====
    custom_prompt = st.text_area("Prompt 模板",
                               height=300,
                               value=st.session_state.llm_config['prompt'],
                               key='prompt_editor',
                               help="使用 {text} 作为内容占位符")

    # ===== 独立密钥输入 =====
    manual_api_key = st.text_input('API 密钥（可选）',
                                 type="password",
                                 value="",
                                 key='manual_api_key',
                                 help="手动输入密钥将覆盖配置文件中的密钥")

    # ===== 配置下载生成 =====
    if st.button("🔒 生成加密配置", key='save_config'):
        if st.session_state.llm_config['api_key'] or manual_api_key:
            # 优先使用手动输入的密钥
            final_api_key = manual_api_key or st.session_state.llm_config['api_key']

            # 构建配置数据
            config_data = {
                "base_url": base_url,
                "engine": engine,
                "api_key": base64.b64encode(encrypt_data(final_api_key, public_key)).decode(),
                "max_tokens": max_tokens,
                "temperature": temperature,
                "prompt": custom_prompt  # 保存当前编辑的prompt
            }

            # 生成下载文件
            st.download_button(
                label="⬇️ 下载当前配置",
                data=json.dumps(config_data, indent=2),
                file_name="llm_config.json",
                mime="application/json"
            )
        else:
            st.warning("需要至少一个API密钥来源（上传配置或手动输入）")

st.title("📝 竞赛解析分步生成器")
input_text = st.text_area("输入题目解析内容：",
                        height=200,
                        placeholder="在此粘贴需要分步的解析内容...")
if st.button("🚀 生成分步解析", type="primary"):
    if input_text:
        try:

            # 调用API（保持原有实现）
            tips = get_custom_api_tips(
                base_url=st.session_state.llm_config['base_url'],
                api_key=manual_api_key or st.session_state.llm_config['api_key'],  # 使用合并后的密钥
                params={
                    'engine': engine,
                    'max_tokens': max_tokens,
                    'temperature': temperature
                },
                text=custom_prompt.format(text=input_text)
            )

            # 初始化显示状态
            st.session_state.tips = tips
            st.session_state.show_step = 0
        except Exception as e:
            st.error(f"生成失败: {str(e)}")
    else:
        st.warning("请填写API密钥和解析内容")

# 分步显示逻辑
if "tips" in st.session_state:
    current_step = st.session_state.show_step
    total_steps = len(st.session_state.tips)

    # 当前步骤内容（直接显示原始内容）
    st.markdown("---")
    st.markdown(st.session_state.tips[current_step])  # 直接显示Markdown内容

    # 分步控制按钮
    col1, col2, _ = st.columns([2, 2, 6])  # 调整比例使按钮靠左
    with col1:
        # 上一步按钮（始终显示，根据状态禁用）
        st.button(
            "← 上一步",
            disabled=(current_step <= 0),
            key="prev",
            on_click=lambda: st.session_state.update(show_step=current_step-1)
        )
    with col2:
        # 下一步按钮（始终显示，根据状态禁用）
        next_disabled = current_step >= total_steps - 1
        btn_label = "完成 ✅" if next_disabled else "→ 下一步"
        st.button(
            btn_label,
            disabled=next_disabled,
            key="next",
            on_click=lambda: st.session_state.update(show_step=current_step+1)
        )

    # 自动显示进度（不显式调用rerun）
    st.progress((current_step + 1) / total_steps)

st.markdown("---")
st.markdown(
    """<div style="text-align: right; color: #888;">
    Developed by
    <span style="font-weight: bold; color: #0068B5;">DeepSeek</span>
    </div>""",
    unsafe_allow_html=True
)

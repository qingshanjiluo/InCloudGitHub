"""
SK密钥分析模块 - 自动识别SK密钥类型、推断对应的Base URL和可用模型
"""
import re
import json
from typing import Dict, List, Optional, Tuple


# ============================================================
# 已知 AI 服务商的 Base URL 和模型映射表
# ============================================================

# OpenAI 系列 (sk-...)
OPENAI_BASE_URL = "https://api.openai.com/v1"
OPENAI_MODELS = [
    "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo",
    "o1", "o1-mini", "o3-mini",
]

# Anthropic Claude (sk-ant-...)
ANTHROPIC_BASE_URL = "https://api.anthropic.com/v1"
ANTHROPIC_MODELS = [
    "claude-sonnet-4-20250514", "claude-opus-4-20250514",
    "claude-sonnet-4", "claude-opus-4",
    "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022",
    "claude-3-opus-20240229", "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307",
]

# Google AI / Gemini (AIza...)
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_MODELS = [
    "gemini-2.0-flash", "gemini-2.0-flash-lite",
    "gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.5-flash-8b",
    "gemini-1.0-pro",
]

# ============================================================
# 中转/代理 API 特征库
# 通过 Base URL 中的关键词识别
# ============================================================

PROXY_API_PATTERNS = [
    # ---- 常见中转站 ----
    {
        "keywords": ["api.ohmygpt.com", "ohmygpt"],
        "name": "OhMyGPT",
        "base_url": "https://api.ohmygpt.com/v1",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4", "gpt-3.5-turbo", "claude-3-5-sonnet"],
        "type": "proxy",
    },
    {
        "keywords": ["api.gptsapi.net", "gptsapi"],
        "name": "GPTSAPI",
        "base_url": "https://api.gptsapi.net/v1",
        "models": ["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet"],
        "type": "proxy",
    },
    {
        "keywords": ["api.302.ai", "302.ai"],
        "name": "302AI",
        "base_url": "https://api.302.ai/v1",
        "models": ["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet", "gemini-1.5-pro"],
        "type": "proxy",
    },
    {
        "keywords": ["api.aiproxy.io", "aiproxy"],
        "name": "AIProxy",
        "base_url": "https://api.aiproxy.io/v1",
        "models": ["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet"],
        "type": "proxy",
    },
    {
        "keywords": ["api.xty.app", "xty"],
        "name": "XTYY",
        "base_url": "https://api.xty.app/v1",
        "models": ["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet"],
        "type": "proxy",
    },
    {
        "keywords": ["api.v3.chat", "v3.chat"],
        "name": "V3Chat",
        "base_url": "https://api.v3.chat/v1",
        "models": ["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet"],
        "type": "proxy",
    },
    {
        "keywords": ["api.deepbricks.ai", "deepbricks"],
        "name": "DeepBricks",
        "base_url": "https://api.deepbricks.ai/v1",
        "models": ["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet"],
        "type": "proxy",
    },
    {
        "keywords": ["api.agicto.cn", "agicto"],
        "name": "AGICTO",
        "base_url": "https://api.agicto.cn/v1",
        "models": ["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet", "deepseek-chat"],
        "type": "proxy",
    },
    {
        "keywords": ["api.chatanywhere.tech", "chatanywhere"],
        "name": "ChatAnywhere",
        "base_url": "https://api.chatanywhere.tech/v1",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
        "type": "proxy",
    },
    {
        "keywords": ["api.openai-proxy.org", "openai-proxy"],
        "name": "OpenAI Proxy",
        "base_url": "https://api.openai-proxy.org/v1",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
        "type": "proxy",
    },
    # ---- 自部署 / 开源项目 ----
    {
        "keywords": ["api.openai.com"],
        "name": "OpenAI Official",
        "base_url": "https://api.openai.com/v1",
        "models": OPENAI_MODELS,
        "type": "official",
    },
    {
        "keywords": ["api.anthropic.com"],
        "name": "Anthropic Official",
        "base_url": "https://api.anthropic.com/v1",
        "models": ANTHROPIC_MODELS,
        "type": "official",
    },
    {
        "keywords": ["generativelanguage.googleapis.com"],
        "name": "Google Gemini Official",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "models": GEMINI_MODELS,
        "type": "official",
    },
    # ---- 国内大模型厂商 ----
    {
        "keywords": ["dashscope.aliyuncs.com", "dashscope"],
        "name": "阿里通义千问 (DashScope)",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": ["qwen-max", "qwen-plus", "qwen-turbo", "qwen2.5-72b-instruct"],
        "type": "domestic",
    },
    {
        "keywords": ["api.siliconflow.cn", "siliconflow"],
        "name": "SiliconFlow (硅基流动)",
        "base_url": "https://api.siliconflow.cn/v1",
        "models": ["deepseek-chat", "deepseek-coder", "Qwen/Qwen2.5-72B-Instruct"],
        "type": "domestic",
    },
    {
        "keywords": ["api.deepseek.com", "deepseek"],
        "name": "DeepSeek Official",
        "base_url": "https://api.deepseek.com/v1",
        "models": ["deepseek-chat", "deepseek-coder", "deepseek-reasoner"],
        "type": "official",
    },
    {
        "keywords": ["api.moonshot.cn", "moonshot"],
        "name": "Moonshot (月之暗面)",
        "base_url": "https://api.moonshot.cn/v1",
        "models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
        "type": "domestic",
    },
    {
        "keywords": ["api.lingyiwanwu.com", "lingyiwanwu"],
        "name": "零一万物 (Yi)",
        "base_url": "https://api.lingyiwanwu.com/v1",
        "models": ["yi-lightning", "yi-medium", "yi-large"],
        "type": "domestic",
    },
    {
        "keywords": ["api.minimax.chat", "minimax"],
        "name": "MiniMax",
        "base_url": "https://api.minimax.chat/v1",
        "models": ["abab6.5s", "abab5.5"],
        "type": "domestic",
    },
    {
        "keywords": ["api.stepfun.com", "stepfun"],
        "name": "阶跃星辰 (StepFun)",
        "base_url": "https://api.stepfun.com/v1",
        "models": ["step-1", "step-1v", "step-2"],
        "type": "domestic",
    },
    {
        "keywords": ["api.zhipu.ai", "zhipuai", "bigmodel.cn"],
        "name": "智谱AI (ZhipuAI)",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "models": ["glm-4-plus", "glm-4", "glm-4-flash"],
        "type": "domestic",
    },
    {
        "keywords": ["api.baidu.com", "qianfan", "baidu"],
        "name": "百度千帆 (QianFan)",
        "base_url": "https://qianfan.baidubce.com/v2",
        "models": ["ERNIE-4.0", "ERNIE-3.5", "ERNIE-Speed"],
        "type": "domestic",
    },
    {
        "keywords": ["api.volcengine.com", "volcengine", "ark"],
        "name": "火山引擎 (Volcengine/ARK)",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "models": ["doubao-pro-32k", "doubao-lite-32k"],
        "type": "domestic",
    },
    {
        "keywords": ["api.tencent.com", "hunyun", "tencent"],
        "name": "腾讯混元 (Hunyuan)",
        "base_url": "https://api.hunyuan.cloud.tencent.com/v1",
        "models": ["hunyuan-pro", "hunyuan-standard"],
        "type": "domestic",
    },
    {
        "keywords": ["api.xiaoai.com", "xiaomi"],
        "name": "小米AI",
        "base_url": "https://api.xiaoai.com/v1",
        "models": ["mi-llm"],
        "type": "domestic",
    },
    # ---- 开源 / 本地部署 ----
    {
        "keywords": ["localhost", "127.0.0.1", "0.0.0.0"],
        "name": "本地部署 (Local)",
        "base_url": None,
        "models": ["自定义模型"],
        "type": "local",
    },
    {
        "keywords": ["ollama"],
        "name": "Ollama (本地)",
        "base_url": "http://localhost:11434/v1",
        "models": ["llama3", "mistral", "qwen2.5", "deepseek-r1"],
        "type": "local",
    },
    {
        "keywords": ["vllm", "vllm"],
        "name": "vLLM (本地部署)",
        "base_url": None,
        "models": ["自定义模型"],
        "type": "local",
    },
    {
        "keywords": ["api.together.xyz", "together"],
        "name": "Together AI",
        "base_url": "https://api.together.xyz/v1",
        "models": ["meta-llama/Llama-3.3-70B-Instruct", "mistralai/Mixtral-8x7B-Instruct"],
        "type": "cloud",
    },
    {
        "keywords": ["api.groq.com", "groq"],
        "name": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "models": ["llama3-70b-8192", "llama3-8b-8192", "mixtral-8x7b-32768"],
        "type": "cloud",
    },
    {
        "keywords": ["api.fireworks.ai", "fireworks"],
        "name": "Fireworks AI",
        "base_url": "https://api.fireworks.ai/inference/v1",
        "models": ["accounts/fireworks/models/llama-v3p3-70b-instruct"],
        "type": "cloud",
    },
    {
        "keywords": ["api.perplexity.ai", "perplexity"],
        "name": "Perplexity AI",
        "base_url": "https://api.perplexity.ai",
        "models": ["sonar-pro", "sonar", "mixtral-8x7b-instruct"],
        "type": "cloud",
    },
    {
        "keywords": ["api.cohere.ai", "cohere"],
        "name": "Cohere",
        "base_url": "https://api.cohere.ai/v1",
        "models": ["command-r-plus", "command-r", "command"],
        "type": "cloud",
    },
    {
        "keywords": ["api.mistral.ai", "mistral"],
        "name": "Mistral AI",
        "base_url": "https://api.mistral.ai/v1",
        "models": ["mistral-large-latest", "mistral-medium-latest", "mistral-small-latest"],
        "type": "cloud",
    },
]


class SKAnalyzer:
    """SK密钥分析器 - 识别密钥类型、推断Base URL和可用模型"""

    # 密钥前缀 -> (服务商, 类型)
    PREFIX_MAP = {
        "sk-proj-": ("OpenAI Project Key", "openai"),
        "sk-ant-": ("Anthropic Claude", "anthropic"),
        "sk-": ("OpenAI", "openai"),
        "AIza": ("Google Gemini", "gemini"),
        "fkey-": ("OpenAI (Fine-tuning)", "openai"),
        "pk-": ("OpenAI Publishable Key", "openai"),
    }

    @staticmethod
    def identify_key_type(secret: str) -> Dict:
        """
        识别密钥类型

        Args:
            secret: 密钥字符串

        Returns:
            包含类型信息的字典
        """
        result = {
            "provider": "unknown",
            "provider_name": "未知服务商",
            "key_type": "unknown",
            "confidence": "low",
        }

        for prefix, (name, provider) in SKAnalyzer.PREFIX_MAP.items():
            if secret.startswith(prefix):
                result["provider"] = provider
                result["provider_name"] = name
                result["key_type"] = "api_key"
                result["confidence"] = "high" if len(secret) > 30 else "medium"
                break

        return result

    @staticmethod
    def infer_base_url_from_context(context_text: str) -> Optional[Dict]:
        """
        从上下文文本中推断 Base URL

        Args:
            context_text: 上下文文本（代码行、配置文件内容等）

        Returns:
            匹配到的服务商信息，未匹配则返回 None
        """
        context_lower = context_text.lower()

        for provider in PROXY_API_PATTERNS:
            for keyword in provider["keywords"]:
                if keyword.lower() in context_lower:
                    return {
                        "name": provider["name"],
                        "base_url": provider["base_url"],
                        "models": provider["models"],
                        "type": provider["type"],
                        "matched_keyword": keyword,
                    }

        return None

    @staticmethod
    def extract_base_url_from_file(content: str) -> List[Dict]:
        """
        从文件内容中提取所有可能的 Base URL

        Args:
            content: 文件内容

        Returns:
            Base URL 信息列表
        """
        # 匹配常见的 base_url / api_base / api_url 等赋值
        url_patterns = [
            r'base_url[\s]*[:=][\s]*["\']([^"\']+)["\']',
            r'api_base[\s]*[:=][\s]*["\']([^"\']+)["\']',
            r'api_url[\s]*[:=][\s]*["\']([^"\']+)["\']',
            r'BASE_URL[\s]*=[\s]*["\']([^"\']+)["\']',
            r'API_BASE[\s]*=[\s]*["\']([^"\']+)["\']',
            r'OPENAI_BASE_URL[\s]*=[\s]*["\']([^"\']+)["\']',
            r'openai_base_url[\s]*[:=][\s]*["\']([^"\']+)["\']',
            r'baseUrl[\s]*[:=][\s]*["\']([^"\']+)["\']',
            r'apiBase[\s]*[:=][\s]*["\']([^"\']+)["\']',
        ]

        results = []
        for pattern in url_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                url = match.group(1).strip()
                # 过滤掉明显的占位符
                if url and not any(p in url.lower() for p in ["your_", "xxx", "example", "localhost"]):
                    provider = SKAnalyzer.infer_base_url_from_context(url)
                    results.append({
                        "url": url,
                        "provider": provider,
                        "matched_pattern": pattern,
                    })

        return results

    @staticmethod
    def extract_model_from_content(content: str) -> List[str]:
        """
        从文件内容中提取使用的模型名称

        Args:
            content: 文件内容

        Returns:
            模型名称列表
        """
        model_patterns = [
            r'model[\s]*[:=][\s]*["\']([^"\']+)["\']',
            r'MODEL[\s]*=[\s]*["\']([^"\']+)["\']',
            r'model_name[\s]*[:=][\s]*["\']([^"\']+)["\']',
            r'MODEL_NAME[\s]*=[\s]*["\']([^"\']+)["\']',
            r'deployment_name[\s]*[:=][\s]*["\']([^"\']+)["\']',
        ]

        models = []
        for pattern in model_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                model = match.group(1).strip()
                if model and len(model) > 2 and len(model) < 100:
                    # 过滤掉明显不是模型名的
                    if not any(p in model.lower() for p in ["your_", "xxx", "example"]):
                        if model not in models:
                            models.append(model)

        return models

    @staticmethod
    def analyze_secret_comprehensive(secret: str, context_lines: List[str] = None,
                                     file_content: str = None) -> Dict:
        """
        综合分析密钥：识别类型 + 推断 Base URL + 推断模型

        Args:
            secret: 密钥字符串
            context_lines: 密钥周围的上下文代码行
            file_content: 整个文件内容（用于提取更多信息）

        Returns:
            综合分析结果
        """
        # 1. 识别密钥类型
        key_info = SKAnalyzer.identify_key_type(secret)

        result = {
            "secret": secret[:12] + "..." + secret[-4:] if len(secret) > 16 else "***",
            "key_info": key_info,
            "base_urls": [],
            "models": [],
            "providers": [],
        }

        # 2. 从上下文中推断 Base URL
        context_text = ""
        if context_lines:
            context_text = "\n".join(context_lines)
        if file_content:
            context_text += "\n" + file_content

        if context_text:
            # 提取显式声明的 Base URL
            explicit_urls = SKAnalyzer.extract_base_url_from_file(context_text)
            for url_info in explicit_urls:
                if url_info["provider"]:
                    result["base_urls"].append(url_info["url"])
                    if url_info["provider"]["name"] not in result["providers"]:
                        result["providers"].append(url_info["provider"]["name"])
                    for m in url_info["provider"]["models"]:
                        if m not in result["models"]:
                            result["models"].append(m)

            # 从上下文中推断（即使没有显式声明）
            inferred = SKAnalyzer.infer_base_url_from_context(context_text)
            if inferred and inferred["base_url"]:
                if inferred["base_url"] not in result["base_urls"]:
                    result["base_urls"].append(inferred["base_url"])
                if inferred["name"] not in result["providers"]:
                    result["providers"].append(inferred["name"])
                for m in inferred["models"]:
                    if m not in result["models"]:
                        result["models"].append(m)

            # 提取模型
            models = SKAnalyzer.extract_model_from_content(context_text)
            for m in models:
                if m not in result["models"]:
                    result["models"].append(m)

        # 3. 根据密钥类型提供默认建议
        if not result["base_urls"]:
            provider = key_info.get("provider")
            if provider == "openai":
                result["base_urls"].append(OPENAI_BASE_URL)
                result["providers"].append("OpenAI Official")
                for m in OPENAI_MODELS[:3]:
                    if m not in result["models"]:
                        result["models"].append(m)
            elif provider == "anthropic":
                result["base_urls"].append(ANTHROPIC_BASE_URL)
                result["providers"].append("Anthropic Official")
                for m in ANTHROPIC_MODELS[:3]:
                    if m not in result["models"]:
                        result["models"].append(m)
            elif provider == "gemini":
                result["base_urls"].append(GEMINI_BASE_URL)
                result["providers"].append("Google Gemini Official")
                for m in GEMINI_MODELS[:3]:
                    if m not in result["models"]:
                        result["models"].append(m)

        return result

    @staticmethod
    def get_all_providers() -> List[Dict]:
        """获取所有已知服务商列表"""
        return [
            {
                "name": p["name"],
                "base_url": p["base_url"],
                "models": p["models"],
                "type": p["type"],
            }
            for p in PROXY_API_PATTERNS
        ]

    @staticmethod
    def get_provider_by_base_url(base_url: str) -> Optional[Dict]:
        """根据 Base URL 查找服务商"""
        for p in PROXY_API_PATTERNS:
            for keyword in p["keywords"]:
                if keyword.lower() in base_url.lower():
                    return {
                        "name": p["name"],
                        "base_url": p["base_url"],
                        "models": p["models"],
                        "type": p["type"],
                    }
        return None

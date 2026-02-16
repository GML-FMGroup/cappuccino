import os
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()


@dataclass
class ModelConfig:
    """模型配置"""
    model: str
    api_key: str
    base_url: Optional[str] = None
    
    def is_complete(self) -> bool:
        """检查配置是否完整"""
        return bool(self.model and self.api_key and self.base_url)


@dataclass
class TelegramConfig:
    """Telegram 配置"""
    enabled: bool = False
    bot_token: str = ""
    allowed_users: List[int] = field(default_factory=list)
    request_timeout: int = 300  # Telegram API 请求超时时间（秒），默认5分钟
    
    def is_complete(self) -> bool:
        """检查配置是否完整"""
        if not self.enabled:
            return True
        return bool(self.bot_token)


@dataclass
class ServerConfig:
    """服务器配置（包含 HTTP API 服务）"""
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    
    def is_complete(self) -> bool:
        """检查配置是否完整"""
        return bool(self.host and self.port)


@dataclass
class URLAPIConfig:
    """HTTP URL API 平台配置"""
    enabled: bool = True
    
    def is_complete(self) -> bool:
        """检查配置是否完整"""
        return self.enabled  # URL API 如果启用，配置就完整


@dataclass
class MemoryConfig:
    """记忆配置"""
    # User Memory 配置（固定使用 SQLite）
    user_max_history: int = 10
    # Task Context Memory 配置
    task_max_memory_steps: int = 20  # 任务执行过程中最多保留多少步
    # Agent 配置
    max_iterations: int = 10  # Agent 最大迭代次数


class Config:
    """统一配置管理器"""
    
    def __init__(self):
        # 服务器配置（HTTP API 服务）
        self.server = ServerConfig(
            host=os.getenv("SERVER_HOST", "0.0.0.0"),
            port=int(os.getenv("SERVER_PORT", "8000")),
            log_level=os.getenv("LOG_LEVEL", "INFO")
        )
        
        # 模型配置 - Planning Model
        self.planning = ModelConfig(
            model=os.getenv("PLANNING_MODEL", ""),
            api_key=os.getenv("PLANNING_API_KEY", ""),
            base_url=os.getenv("PLANNING_BASE_URL", "")
        )
        
        # 模型配置 - Grounding Model
        self.grounding = ModelConfig(
            model=os.getenv("GROUNDING_MODEL", ""),
            api_key=os.getenv("GROUNDING_API_KEY", ""),
            base_url=os.getenv("GROUNDING_BASE_URL", "")
        )
        
        # 记忆配置
        self.memory = MemoryConfig(
            user_max_history=int(os.getenv("USER_MAX_HISTORY", "10")),
            task_max_memory_steps=int(os.getenv("TASK_MAX_MEMORY_STEPS", "10")),
            max_iterations=int(os.getenv("MAX_ITERATIONS", "10"))
        )
        
        # URL API 平台配置
        self.url_api = URLAPIConfig(
            enabled=os.getenv("URL_API_ENABLED", "true").lower() == "true"
        )
        
        # Telegram 配置
        self.telegram = TelegramConfig(
            enabled=os.getenv("TELEGRAM_ENABLED", "false").lower() == "true",
            bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            allowed_users=self._parse_user_list(os.getenv("TELEGRAM_ALLOWED_USERS", "")),
            request_timeout=int(os.getenv("TELEGRAM_REQUEST_TIMEOUT", "300"))
        )
    
    @staticmethod
    def _parse_user_list(user_string: str) -> List[int]:
        """解析用户列表字符串"""
        if not user_string:
            return []
        return [int(uid.strip()) for uid in user_string.split(",") if uid.strip().isdigit()]
    
    def validate(self) -> Dict[str, bool]:
        """验证配置，返回各部分的验证结果"""
        results = {}
        
        # 验证服务器配置
        if self.server.is_complete():
            print(f"✅ 服务器配置正常")
            results["server"] = True
        else:
            print("❌ 服务器配置不完整")
            results["server"] = False
        
        # 验证模型配置
        if self.planning.is_complete():
            print("✅ Planning 模型配置正常")
            results["planning"] = True
        else:
            print("❌ Planning 模型配置不完整")
            results["planning"] = False
        
        if self.grounding.is_complete():
            print("✅ Grounding 模型配置正常")
            results["grounding"] = True
        else:
            print("❌ Grounding 模型配置不完整")
            results["grounding"] = False
        
        # 验证 URL API 配置
        if self.url_api.is_complete():
            if self.url_api.enabled:
                print("✅ URL API 平台已启用")
            else:
                print("⊘ URL API 平台未启用")
            results["url_api"] = True
        else:
            print("❌ URL API 配置不完整")
            results["url_api"] = False
            
        # 验证 Telegram 配置
        if self.telegram.is_complete():
            if self.telegram.enabled:
                print("✅ Telegram 配置正常")
                if not self.telegram.allowed_users:
                    print("⚠️  Telegram 未设置用户白名单，任何人都可以使用")
            else:
                print("⊘ Telegram 未启用")
            results["telegram"] = True
        else:
            print("❌ Telegram 配置不完整")
            results["telegram"] = False
        
        return results
    
    def get_model_config(self, model_type: str, override: Optional[Dict] = None) -> Dict:
        """获取模型配置，支持请求覆盖
        
        Args:
            model_type: "planning" 或 "grounding"
            override: 可选的覆盖配置
        """
        model_config = getattr(self, model_type, None)
        if model_config is None:
            raise ValueError(f"Unknown model type: {model_type}")
        
        config_dict = {
            "model": model_config.model,
            "api_key": model_config.api_key,
            "base_url": model_config.base_url or ""
        }
        
        # 请求值优先于配置值
        if override:
            for key, value in override.items():
                if value and key in config_dict:
                    config_dict[key] = value
        
        return config_dict


# 全局配置实例
config = Config()

"""
Skills Loader - 动态技能加载系统

实现 Skills 渐进式加载：
- 目录发现
- 运行时动态加载
- 技能执行接口

设计参考：
- Claude Code Skills System
- OpenAI Plugins
- FastMCP Tools
"""
import asyncio
import importlib
import importlib.util
import inspect
import json
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from loguru import logger


class SkillStatus(Enum):
    """技能状态"""
    DISCOVERED = "discovered"
    LOADING = "loading"
    LOADED = "loaded"
    FAILED = "failed"
    DISABLED = "disabled"


class SkillMetadata:
    """技能元数据"""

    def __init__(
        self,
        name: str,
        description: str,
        version: str = "1.0.0",
        author: Optional[str] = None,
        tags: Optional[List[str]] = None,
        triggers: Optional[List[str]] = None,
    ):
        self.name = name
        self.description = description
        self.version = version
        self.author = author
        self.tags = tags or []
        self.triggers = triggers or []

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillMetadata":
        return cls(
            name=data.get("name", "unknown"),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            author=data.get("author"),
            tags=data.get("tags", []),
            triggers=data.get("triggers", []),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "tags": self.tags,
            "triggers": self.triggers,
        }


class BaseSkill(ABC):
    """技能基类"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._enabled = True

    @property
    @abstractmethod
    def metadata(self) -> SkillMetadata:
        """返回技能元数据"""
        pass

    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行技能

        Args:
            context: 执行上下文

        Returns:
            执行结果
        """
        pass

    def enable(self):
        """启用技能"""
        self._enabled = True

    def disable(self):
        """禁用技能"""
        self._enabled = False

    @property
    def is_enabled(self) -> bool:
        """检查是否启用"""
        return self._enabled


class Skill(ABC):
    """轻量级技能接口 - 用于非类基础的技能"""

    def __init__(self, name: str, handler: Callable):
        self.name = name
        self.handler = handler
        self._enabled = True

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name=self.name,
            description=f"Skill: {self.name}",
        )

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        result = self.handler(context)
        if asyncio.iscoroutine(result):
            return await result
        return result

    def enable(self):
        self._enabled = True

    def disable(self):
        self._enabled = False

    @property
    def is_enabled(self) -> bool:
        return self._enabled


class SkillsLoader:
    """
    Skills 动态加载器

    特性：
    - 目录扫描发现
    - 动态导入
    - 运行时热加载
    - 依赖管理
    """

    def __init__(self, skills_dir: str = "skills"):
        """
        初始化技能加载器

        Args:
            skills_dir: 技能目录路径
        """
        self.skills_dir = Path(skills_dir)
        self.skills: Dict[str, BaseSkill] = {}
        self.skill_metadata: Dict[str, SkillMetadata] = {}
        self.skill_status: Dict[str, SkillStatus] = {}

        # 配置
        self.auto_discover = True
        self.auto_load = True

    def discover_skills(self) -> List[str]:
        """
        发现技能

        Returns:
            发现的技能名称列表
        """
        discovered = []

        if not self.skills_dir.exists():
            logger.warning(f"⚠️ 技能目录不存在: {self.skills_dir}")
            return discovered

        # 扫描目录
        for item in self.skills_dir.iterdir():
            if item.is_dir() and not item.name.startswith("_"):
                # 查找 skill.py 或 __init__.py
                skill_file = item / "skill.py"
                init_file = item / "__init__.py"

                if skill_file.exists() or init_file.exists():
                    discovered.append(item.name)
                    self.skill_status[item.name] = SkillStatus.DISCOVERED
                    logger.info(f"🔍 发现技能: {item.name}")

                # 查找 skill.json 元数据
                meta_file = item / "skill.json"
                if meta_file.exists():
                    try:
                        meta = json.loads(meta_file.read_text())
                        self.skill_metadata[item.name] = SkillMetadata.from_dict(meta)
                    except Exception as e:
                        logger.warning(f"⚠️ 技能元数据解析失败 {item.name}: {e}")

        logger.info(f"🔍 发现 {len(discovered)} 个技能")
        return discovered

    def load_skill(self, skill_name: str) -> bool:
        """
        加载单个技能

        Args:
            skill_name: 技能名称

        Returns:
            是否加载成功
        """
        if skill_name in self.skills:
            logger.info(f"⚡ 技能已加载: {skill_name}")
            return True

        self.skill_status[skill_name] = SkillStatus.LOADING

        try:
            # 动态导入模块
            skill_path = self.skills_dir / skill_name

            # 尝试导入
            module_name = f"skills.{skill_name}"

            # 方法1: 尝试 skill.py
            skill_file = skill_path / "skill.py"
            if skill_file.exists():
                spec = importlib.util.spec_from_file_location(
                    module_name, skill_file
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    # 查找技能类
                    for name, obj in inspect.getmembers(module):
                        if inspect.isclass(obj) and issubclass(obj, BaseSkill) and obj != BaseSkill:
                            skill_instance = obj()
                            self.skills[skill_name] = skill_instance
                            self.skill_metadata[skill_name] = skill_instance.metadata
                            self.skill_status[skill_name] = SkillStatus.LOADED
                            logger.info(f"⚡ 加载技能成功: {skill_name}")
                            return True

            # 方法2: 尝试 __init__.py
            init_file = skill_path / "__init__.py"
            if init_file.exists():
                spec = importlib.util.spec_from_file_location(
                    module_name, init_file
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    for name, obj in inspect.getmembers(module):
                        if inspect.isclass(obj) and issubclass(obj, BaseSkill) and obj != BaseSkill:
                            skill_instance = obj()
                            self.skills[skill_name] = skill_instance
                            self.skill_metadata[skill_name] = skill_instance.metadata
                            self.skill_status[skill_name] = SkillStatus.LOADED
                            logger.info(f"⚡ 加载技能成功: {skill_name}")
                            return True

            logger.warning(f"⚠️ 未找到技能类: {skill_name}")
            self.skill_status[skill_name] = SkillStatus.FAILED
            return False

        except Exception as e:
            logger.error(f"❌ 加载技能失败 {skill_name}: {e}")
            self.skill_status[skill_name] = SkillStatus.FAILED
            return False

    def load_all(self) -> int:
        """
        加载所有发现的技能

        Returns:
            成功加载的数量
        """
        if self.auto_discover:
            self.discover_skills()

        loaded = 0
        for skill_name in self.skill_status.keys():
            if self.skill_status[skill_name] == SkillStatus.DISCOVERED:
                if self.load_skill(skill_name):
                    loaded += 1

        logger.info(f"⚡ 加载了 {loaded}/{len(self.skill_status)} 个技能")
        return loaded

    def unload_skill(self, skill_name: str) -> bool:
        """
        卸载技能

        Args:
            skill_name: 技能名称

        Returns:
            是否卸载成功
        """
        if skill_name in self.skills:
            del self.skills[skill_name]
            self.skill_status[skill_name] = SkillStatus.DISCOVERED
            logger.info(f"🗑️ 卸载技能: {skill_name}")
            return True

        return False

    def reload_skill(self, skill_name: str) -> bool:
        """
        重新加载技能

        Args:
            skill_name: 技能名称

        Returns:
            是否重新加载成功
        """
        self.unload_skill(skill_name)
        return self.load_skill(skill_name)

    def get_skill(self, skill_name: str) -> Optional[BaseSkill]:
        """获取技能实例"""
        return self.skills.get(skill_name)

    async def execute_skill(
        self,
        skill_name: str,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        执行技能

        Args:
            skill_name: 技能名称
            context: 执行上下文

        Returns:
            执行结果
        """
        skill = self.get_skill(skill_name)

        if not skill:
            logger.warning(f"⚠️ 技能不存在: {skill_name}")
            return None

        if not skill.is_enabled:
            logger.warning(f"⚠️ 技能已禁用: {skill_name}")
            return None

        try:
            result = await skill.execute(context)
            return result
        except Exception as e:
            logger.error(f"❌ 技能执行失败 {skill_name}: {e}")
            return {"error": str(e)}

    def list_skills(self) -> List[str]:
        """列出所有技能名称"""
        return list(self.skills.keys())

    def get_skill_info(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """获取技能信息"""
        if skill_name not in self.skills:
            return None

        skill = self.skills[skill_name]
        metadata = self.skill_metadata.get(skill_name)

        return {
            "name": skill_name,
            "metadata": metadata.to_dict() if metadata else None,
            "status": self.skill_status.get(skill_name, SkillStatus.LOADED).value,
            "enabled": skill.is_enabled,
        }

    def list_skill_infos(self) -> List[Dict[str, Any]]:
        """列出所有技能信息"""
        return [
            self.get_skill_info(name)
            for name in self.skills.keys()
        ]

    def enable_skill(self, skill_name: str) -> bool:
        """启用技能"""
        skill = self.get_skill(skill_name)
        if skill:
            skill.enable()
            logger.info(f"✅ 启用技能: {skill_name}")
            return True
        return False

    def disable_skill(self, skill_name: str) -> bool:
        """禁用技能"""
        skill = self.get_skill(skill_name)
        if skill:
            skill.disable()
            logger.info(f"⏸️ 禁用技能: {skill_name}")
            return True
        return False

    def register_skill(self, skill: BaseSkill) -> bool:
        """
        注册技能实例

        Args:
            skill: 技能实例

        Returns:
            是否注册成功
        """
        name = skill.metadata.name

        if name in self.skills:
            logger.warning(f"⚠️ 技能已存在: {name}")
            return False

        self.skills[name] = skill
        self.skill_metadata[name] = skill.metadata
        self.skill_status[name] = SkillStatus.LOADED

        logger.info(f"⚡ 注册技能: {name}")
        return True


# 全局实例
_skills_loader: Optional[SkillsLoader] = None


def get_skills_loader() -> SkillsLoader:
    """获取全局技能加载器"""
    global _skills_loader
    if _skills_loader is None:
        _skills_loader = SkillsLoader()
    return _skills_loader

"""
Skills Integration - 技能系统集成

集成增强的技能系统组件：
- SkillGate: 门控检查
- ToolPolicy: 工具策略
- SkillRegistry: 版本管理

这个模块提供统一的接口来使用所有技能组件。
"""
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from loguru import logger

# 导入所有组件
from src.skills.gate import (
    SkillGate,
    SkillMetadata,
    GateResult,
    check_skill,
    create_skill_metadata,
)
from src.skills.policy import (
    ToolPolicy,
    PolicyEffect,
    CORE_TOOLS,
    get_default_policy,
    is_tool_allowed,
)
from src.skills.registry import (
    SkillRegistry,
    SkillVersion,
    SkillInfo,
    SkillUpdate,
    parse_version,
    compare_versions,
)


class SkillsIntegration:
    """技能系统集成

    提供统一的接口来使用所有增强的技能组件：
    1. SkillGate: 门控检查
    2. ToolPolicy: 工具策略
    3. SkillRegistry: 版本管理
    """

    # 三层优先级目录
    PRIORITY_WORKSPACE = 100  # <project>/skills/
    PRIORITY_MANAGED = 50    # ~/.message-agent/skills/
    PRIORITY_BUNDLED = 0     # <install>/skills/

    def __init__(
        self,
        project_skills_dir: str = "skills",
        managed_skills_dir: Optional[str] = None,
        bundled_skills_dir: Optional[str] = None,
        lock_file: Optional[Path] = None,
    ):
        """初始化集成

        Args:
            project_skills_dir: 项目技能目录
            managed_skills_dir: 托管技能目录
            bundled_skills_dir: 打包技能目录
            lock_file: 版本锁定文件
        """
        # 目录配置
        self.project_skills_dir = Path(project_skills_dir)
        self.managed_skills_dir = Path(managed_skills_dir) if managed_skills_dir else Path.home() / ".message-agent" / "skills"
        self.bundled_skills_dir = Path(bundled_skills_dir) if bundled_skills_dir else Path(__file__).parent / "bundled"

        # 初始化组件
        self.gate = SkillGate()
        self.policy = get_default_policy()
        self.registry = SkillRegistry(lock_file=lock_file)

        # 技能缓存
        self._skills: Dict[str, Any] = {}

        logger.info(f"SkillsIntegration initialized")
        logger.info(f"  Project: {self.project_skills_dir}")
        logger.info(f"  Managed: {self.managed_skills_dir}")
        logger.info(f"  Bundled: {self.bundled_skills_dir}")

    # ==================== 技能发现 ====================

    def discover_skills(self) -> List[str]:
        """发现所有技能

        Returns:
            List[str]: 技能名称列表
        """
        discovered = []

        # 1. 发现打包技能 (最低优先级)
        discovered.extend(self._discover_from_dir(
            self.bundled_skills_dir,
            self.PRIORITY_BUNDLED
        ))

        # 2. 发现托管技能
        discovered.extend(self._discover_from_dir(
            self.managed_skills_dir,
            self.PRIORITY_MANAGED
        ))

        # 3. 发现项目技能 (最高优先级)
        discovered.extend(self._discover_from_dir(
            self.project_skills_dir,
            self.PRIORITY_WORKSPACE
        ))

        return list(set(discovered))

    def _discover_from_dir(self, skills_dir: Path, priority: int) -> List[str]:
        """从目录发现技能

        Args:
            skills_dir: 技能目录
            priority: 优先级

        Returns:
            List[str]: 技能名称列表
        """
        discovered = []

        if not skills_dir.exists():
            logger.debug(f"Skills directory not found: {skills_dir}")
            return discovered

        # 扫描目录
        for item in skills_dir.iterdir():
            if not item.is_dir() or item.name.startswith("_"):
                continue

            # 查找技能文件
            skill_file = item / "skill.py"
            init_file = item / "__init__.py"

            if not (skill_file.exists() or init_file.exists()):
                continue

            skill_name = item.name
            discovered.append(skill_name)

            # 门控检查
            gate_result = self.gate.check(item)

            if not gate_result.can_load:
                logger.warning(f"Skill {skill_name} gate check failed: {gate_result.message}")
                continue

            # 解析元数据
            metadata = self._parse_skill_metadata(item, priority)
            if metadata:
                # 注册到版本注册表
                self.registry.register(
                    name=metadata.name,
                    version=SkillVersion.parse(metadata.version),
                    path=item,
                    description=metadata.description,
                    dependencies=metadata.dependencies,
                    priority=priority
                )

            logger.info(f"Discovered skill: {skill_name} (priority={priority})")

        return discovered

    def _parse_skill_metadata(self, skill_path: Path, priority: int) -> Optional[SkillMetadata]:
        """解析技能元数据

        Args:
            skill_path: 技能路径
            priority: 优先级

        Returns:
            Optional[SkillMetadata]: 元数据
        """
        import yaml

        # 尝试 SKILL.md
        skill_md = skill_path / "SKILL.md"
        if skill_md.exists():
            try:
                content = skill_md.read_text(encoding="utf-8")

                # 解析 YAML frontmatter
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        yaml_content = parts[1].strip()
                        data = yaml.safe_load(yaml_content)

                        if data:
                            return SkillMetadata(
                                name=data.get("name", skill_path.name),
                                version=data.get("version", "1.0.0"),
                                description=data.get("description", ""),
                                requires=data.get("requires", {}),
                                platforms=data.get("platforms", []),
                                entry=data.get("entry", "skill.py"),
                                dependencies=data.get("dependencies", []),
                            )
            except Exception as e:
                logger.warning(f"Failed to parse SKILL.md for {skill_path.name}: {e}")

        return None

    # ==================== 技能加载 ====================

    def load_skill(self, skill_name: str) -> bool:
        """加载技能

        Args:
            skill_name: 技能名称

        Returns:
            bool: 是否加载成功
        """
        # 获取技能信息
        skill_info = self.registry.get(skill_name)
        if not skill_info:
            logger.error(f"Skill not found: {skill_name}")
            return False

        # 门控检查
        gate_result = self.gate.check(skill_info.path)
        if not gate_result.can_load:
            logger.warning(f"Skill {skill_name} gate check failed: {gate_result.message}")
            return False

        # 加载技能模块
        try:
            import importlib.util
            skill_file = skill_info.path / "skill.py"

            if not skill_file.exists():
                skill_file = skill_info.path / "__init__.py"

            if not skill_file.exists():
                logger.error(f"Skill file not found: {skill_name}")
                return False

            # 动态导入
            spec = importlib.util.spec_from_file_location(skill_name, skill_file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # 查找技能类
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and issubclass(attr, object):
                        if hasattr(attr, "metadata") and hasattr(attr, "execute"):
                            self._skills[skill_name] = attr()
                            logger.info(f"Loaded skill: {skill_name}")
                            return True

            logger.error(f"No skill class found in {skill_name}")
            return False

        except Exception as e:
            logger.error(f"Failed to load skill {skill_name}: {e}")
            return False

    def unload_skill(self, skill_name: str) -> bool:
        """卸载技能

        Args:
            skill_name: 技能名称

        Returns:
            bool: 是否卸载成功
        """
        if skill_name in self._skills:
            del self._skills[skill_name]
            logger.info(f"Unloaded skill: {skill_name}")
            return True
        return False

    # ==================== 工具策略 ====================

    def is_tool_allowed(self, tool_name: str, agent_id: Optional[str] = None) -> bool:
        """检查工具是否允许

        Args:
            tool_name: 工具名称
            agent_id: Agent ID

        Returns:
            bool: 是否允许
        """
        return self.policy.is_allowed(tool_name, agent_id)

    def add_tool_policy(
        self,
        tool_pattern: str,
        effect: PolicyEffect,
        agent_id: Optional[str] = None
    ):
        """添加工具策略

        Args:
            tool_pattern: 工具模式
            effect: 效果
            agent_id: Agent ID
        """
        self.policy.add_rule(tool_pattern, effect, agent_id)

    def get_allowed_tools(self, agent_id: Optional[str] = None) -> Set[str]:
        """获取允许的工具列表

        Args:
            agent_id: Agent ID

        Returns:
            Set[str]: 允许的工具集合
        """
        return self.policy.get_allowed_tools(agent_id)

    # ==================== 版本管理 ====================

    def lock_skill_version(self, skill_name: str, version: str):
        """锁定技能版本

        Args:
            skill_name: 技能名称
            version: 版本
        """
        self.registry.lock(skill_name, version)

    def unlock_skill_version(self, skill_name: str):
        """解锁技能版本

        Args:
            skill_name: 技能名称
        """
        self.registry.unlock(skill_name)

    def get_skill_version(self, skill_name: str) -> Optional[str]:
        """获取技能版本

        Args:
            skill_name: 技能名称

        Returns:
            Optional[str]: 版本字符串
        """
        skill_info = self.registry.get(skill_name)
        return str(skill_info.version) if skill_info else None

    def list_skills(self) -> List[Dict[str, Any]]:
        """列出所有技能

        Returns:
            List[Dict]: 技能信息列表
        """
        return [
            {
                "name": info.name,
                "version": str(info.version),
                "priority": info.priority,
                "path": str(info.path),
                "description": info.description,
            }
            for info in self.registry.list_skills()
        ]

    # ==================== 状态 ====================

    def get_status(self) -> Dict[str, Any]:
        """获取状态

        Returns:
            Dict: 状态信息
        """
        return {
            "loaded_skills": list(self._skills.keys()),
            "registered_skills": len(self.registry.list_skills()),
            "policy": self.policy.to_dict(),
            "directories": {
                "project": str(self.project_skills_dir),
                "managed": str(self.managed_skills_dir),
                "bundled": str(self.bundled_skills_dir),
            }
        }


# ==================== 全局实例 ====================

_default_integration: Optional[SkillsIntegration] = None


def get_skills_integration() -> SkillsIntegration:
    """获取默认集成实例

    Returns:
        SkillsIntegration: 集成实例
    """
    global _default_integration
    if _default_integration is None:
        _default_integration = SkillsIntegration()
    return _default_integration


def create_skills_integration(**kwargs) -> SkillsIntegration:
    """创建新的集成实例

    Args:
        **kwargs: 初始化参数

    Returns:
        SkillsIntegration: 集成实例
    """
    return SkillsIntegration(**kwargs)

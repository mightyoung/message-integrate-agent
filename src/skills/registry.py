"""
Skill Registry - 技能版本管理

实现技能版本管理：
- 语义版本解析
- 版本锁定
- 依赖解析

参考:
- 语义版本: https://semver.org/
- PEP 440: Python 版本标识
"""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from loguru import logger


@dataclass
class SkillVersion:
    """语义版本"""
    major: int = 0
    minor: int = 0
    patch: int = 0

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def __lt__(self, other: "SkillVersion") -> bool:
        return (self.major, self.minor, self.patch) < (other.major, other.minor, self.patch)

    def __le__(self, other: "SkillVersion") -> bool:
        return self == other or self < other

    def __gt__(self, other: "SkillVersion") -> bool:
        return not self <= other

    def __ge__(self, other: "SkillVersion") -> bool:
        return not self < other

    @classmethod
    def parse(cls, version: str) -> "SkillVersion":
        """解析版本字符串

        Args:
            version: 版本字符串 (如 "1.2.3")

        Returns:
            SkillVersion: 版本对象
        """
        # 清理版本字符串
        version = version.strip().lstrip("vV")

        # 匹配语义版本
        match = re.match(r"(\d+)\.(\d+)\.(\d+)", version)
        if match:
            return cls(
                major=int(match.group(1)),
                minor=int(match.group(2)),
                patch=int(match.group(3))
            )

        # 简化版本
        parts = version.split(".")
        return cls(
            major=int(parts[0]) if parts else 0,
            minor=int(parts[1]) if len(parts) > 1 else 0,
            patch=int(parts[2]) if len(parts) > 2 else 0
        )

    def is_compatible(self, other: "SkillVersion") -> bool:
        """检查兼容性

        Args:
            other: 另一个版本

        Returns:
            bool: 是否兼容（主版本相同）
        """
        return self.major == other.major


@dataclass
class SkillInfo:
    """技能信息"""
    name: str
    version: SkillVersion
    path: Path
    description: str = ""
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # 0: bundled, 50: managed, 100: workspace


@dataclass
class SkillUpdate:
    """技能更新信息"""
    name: str
    current_version: SkillVersion
    latest_version: SkillVersion
    update_type: str  # major/minor/patch


class SkillRegistry:
    """技能注册表

    管理技能的版本和依赖：
    1. 三层优先级：workspace > managed > bundled
    2. 版本锁定
    3. 依赖解析
    """

    # 优先级
    PRIORITY_WORKSPACE = 100
    PRIORITY_MANAGED = 50
    PRIORITY_BUNDLED = 0

    def __init__(self, lock_file: Optional[Path] = None):
        """初始化注册表

        Args:
            lock_file: 版本锁定文件路径
        """
        self.lock_file = lock_file or Path(".learnings/skills.lock")
        self._skills: Dict[str, SkillInfo] = {}
        self._lock_data: Dict[str, str] = {}  # name -> version

        # 加载锁定数据
        self._load_lock()

        logger.info(f"SkillRegistry initialized, lock file: {self.lock_file}")

    def register(
        self,
        name: str,
        version: SkillVersion,
        path: Path,
        description: str = "",
        dependencies: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        priority: int = 0
    ):
        """注册技能

        Args:
            name: 技能名称
            version: 版本
            path: 技能路径
            description: 描述
            dependencies: 依赖
            metadata: 元数据
            priority: 优先级
        """
        # 检查是否已存在
        existing = self._skills.get(name)
        if existing:
            # 如果新版本优先级更高或版本更新，替换
            if priority > existing.priority or version > existing.version:
                self._skills[name] = SkillInfo(
                    name=name,
                    version=version,
                    path=path,
                    description=description,
                    dependencies=dependencies or [],
                    metadata=metadata or {},
                    priority=priority
                )
                logger.info(f"Replaced skill: {name} -> {version}")
        else:
            self._skills[name] = SkillInfo(
                name=name,
                version=version,
                path=path,
                description=description,
                dependencies=dependencies or [],
                metadata=metadata or {},
                priority=priority
            )
            logger.info(f"Registered skill: {name} v{version}")

    def unregister(self, name: str) -> bool:
        """注销技能

        Args:
            name: 技能名称

        Returns:
            bool: 是否成功注销
        """
        if name in self._skills:
            del self._skills[name]
            logger.info(f"Unregistered skill: {name}")
            return True
        return False

    def get(self, name: str, version: Optional[str] = None) -> Optional[SkillInfo]:
        """获取技能

        Args:
            name: 技能名称
            version: 版本要求

        Returns:
            Optional[SkillInfo]: 技能信息
        """
        skill = self._skills.get(name)
        if not skill:
            return None

        # 检查版本
        if version:
            if version == "latest":
                return skill

            required = SkillVersion.parse(version)
            if not skill.version.is_compatible(required):
                return None

        return skill

    def list_skills(self) -> List[SkillInfo]:
        """列出所有技能

        Returns:
            List[SkillInfo]: 技能列表
        """
        return list(self._skills.values())

    def list_updates(self) -> List[SkillUpdate]:
        """列出可用更新

        Returns:
            List[SkillUpdate]: 更新列表
        """
        updates = []

        # TODO: 从远程注册表检查更新
        # 当前返回空列表
        logger.info("list_updates not implemented - requires remote registry")

        return updates

    def resolve(self, name: str, version: str = "latest") -> Optional[SkillInfo]:
        """解析技能版本

        Args:
            name: 技能名称
            version: 版本要求

        Returns:
            Optional[SkillInfo]: 技能信息
        """
        # 检查锁定版本
        locked_version = self._lock_data.get(name)
        if locked_version and version == "latest":
            version = locked_version

        return self.get(name, version)

    def lock(self, name: str, version: str):
        """锁定技能版本

        Args:
            name: 技能名称
            version: 版本
        """
        self._lock_data[name] = version
        self._save_lock()
        logger.info(f"Locked {name} to version {version}")

    def unlock(self, name: str):
        """解锁技能版本

        Args:
            name: 技能名称
        """
        if name in self._lock_data:
            del self._lock_data[name]
            self._save_lock()
            logger.info(f"Unlocked {name}")

    def get_dependencies(self, name: str) -> List[str]:
        """获取技能依赖

        Args:
            name: 技能名称

        Returns:
            List[str]: 依赖列表
        """
        skill = self._skills.get(name)
        return skill.dependencies if skill else []

    def resolve_dependencies(self, name: str) -> Set[str]:
        """解析依赖树

        Args:
            name: 技能名称

        Returns:
            Set[str]: 所有依赖（包含传递依赖）
        """
        resolved = set()
        to_resolve = [name]

        while to_resolve:
            current = to_resolve.pop()
            if current in resolved:
                continue

            resolved.add(current)

            # 获取依赖
            deps = self.get_dependencies(current)
            for dep in deps:
                if dep not in resolved:
                    to_resolve.append(dep)

        return resolved

    def _load_lock(self):
        """加载锁定数据"""
        if self.lock_file.exists():
            try:
                data = json.loads(self.lock_file.read_text())
                self._lock_data = data.get("skills", {})
                logger.info(f"Loaded {len(self._lock_data)} locked versions")
            except Exception as e:
                logger.warning(f"Failed to load lock file: {e}")

    def _save_lock(self):
        """保存锁定数据"""
        try:
            self.lock_file.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "skills": self._lock_data,
                "updated_at": str(Path(__file).stat().st_mtime)
            }

            self.lock_file.write_text(json.dumps(data, indent=2))
            logger.debug(f"Saved lock file: {self.lock_file}")

        except Exception as e:
            logger.error(f"Failed to save lock file: {e}")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典

        Returns:
            Dict: 注册表字典
        """
        return {
            "skills": {
                name: {
                    "version": str(info.version),
                    "path": str(info.path),
                    "priority": info.priority,
                    "dependencies": info.dependencies
                }
                for name, info in self._skills.items()
            },
            "locked": self._lock_data
        }


# ==================== 便捷函数 ====================

def parse_version(version: str) -> SkillVersion:
    """解析版本字符串

    Args:
        version: 版本字符串

    Returns:
        SkillVersion: 版本
    """
    return SkillVersion.parse(version)


def compare_versions(v1: str, v2: str) -> int:
    """比较版本

    Args:
        v1: 版本1
        v2: 版本2

    Returns:
        int: -1, 0, 1
    """
    sv1 = SkillVersion.parse(v1)
    sv2 = SkillVersion.parse(v2)

    if sv1 < sv2:
        return -1
    elif sv1 > sv2:
        return 1
    return 0


# ==================== 测试 ====================

if __name__ == "__main__":
    # 测试
    registry = SkillRegistry()

    # 注册技能
    registry.register(
        "web_search",
        SkillVersion.parse("1.2.0"),
        Path("/skills/web_search"),
        description="Web search skill",
        dependencies=["api_client"],
        priority=100
    )

    registry.register(
        "api_client",
        SkillVersion.parse("1.0.0"),
        Path("/skills/api_client"),
        description="API client",
        priority=100
    )

    # 解析依赖
    deps = registry.resolve_dependencies("web_search")
    print(f"Dependencies: {deps}")

    # 锁定版本
    registry.lock("api_client", "1.0.0")

    # 列出技能
    skills = registry.list_skills()
    print(f"Registered skills: {[s.name for s in skills]}")

    # 版本比较
    print(f"1.2.0 > 1.1.0: {compare_versions('1.2.0', '1.1.0')}")
    print(f"2.0.0 compatible with 1.0.0: {SkillVersion.parse('2.0.0').is_compatible(SkillVersion.parse('1.0.0'))}")

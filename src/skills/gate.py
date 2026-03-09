"""
Skill Gate - 技能门控检查

实现 OpenClaw 风格的技能门控机制：
- YAML frontmatter 解析
- 环境要求检查 (binary, env, config, platforms)

参考:
- OpenClaw: Skill loading with YAML frontmatter gating
- https://gist.github.com/royosherove/971c7b4a350a30ac8a8dad41604a95a0
"""
import asyncio
import os
import platform
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


@dataclass
class SkillMetadata:
    """技能元数据"""
    name: str
    version: str = "1.0.0"
    description: str = ""
    requires: Dict[str, Any] = field(default_factory=dict)
    platforms: List[str] = field(default_factory=list)
    platforms_exclude: List[str] = field(default_factory=list)
    entry: str = "skill.py"
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GateResult:
    """门控检查结果"""
    can_load: bool
    missing_requirements: List[str] = field(default_factory=list)
    platform_mismatch: bool = False
    message: str = ""

    def __post_init__(self):
        if not self.can_load and not self.message:
            self.message = f"Cannot load: {', '.join(self.missing_requirements)}"


class SkillGate:
    """技能门控检查器

    检查技能是否满足加载条件：
    1. 二进制依赖检查
    2. 环境变量检查
    3. 配置文件检查
    4. 平台兼容性检查
    """

    def __init__(self):
        """初始化门控检查器"""
        self._binary_cache: Dict[str, bool] = {}

    async def check(self, skill_path: Path) -> GateResult:
        """检查技能是否满足加载条件

        Args:
            skill_path: 技能目录路径

        Returns:
            GateResult: 检查结果
        """
        # 查找 SKILL.md 文件
        skill_md = skill_path / "SKILL.md"

        if not skill_md.exists():
            # 尝试 skill.yaml
            skill_yaml = skill_path / "skill.yaml"
            if skill_yaml.exists():
                skill_md = skill_yaml
            else:
                # 没有元数据文件，允许加载
                return GateResult(can_load=True, message="No metadata file, allow load")

        try:
            # 解析元数据
            metadata = await self._parse_metadata(skill_md)
            if not metadata:
                return GateResult(can_load=True, message="Empty metadata, allow load")

            # 检查各项要求
            missing = []

            # 1. 检查二进制依赖
            binary_missing = await self._check_binaries(metadata.requires.get("binary", []))
            missing.extend(binary_missing)

            # 2. 检查环境变量
            env_missing = await self._check_env_vars(metadata.requires.get("env", []))
            missing.extend(env_missing)

            # 3. 检查配置文件
            config_missing = await self._check_configs(metadata.requires.get("config", []))
            missing.extend(config_missing)

            # 4. 检查平台兼容性
            platform_ok = self._check_platform(metadata.platforms, metadata.platforms_exclude)
            if not platform_ok:
                return GateResult(
                    can_load=False,
                    missing_requirements=missing,
                    platform_mismatch=True,
                    message=f"Platform {platform.system()} not supported"
                )

            if missing:
                return GateResult(
                    can_load=False,
                    missing_requirements=missing,
                    message=f"Missing requirements: {', '.join(missing)}"
                )

            return GateResult(can_load=True, message="All checks passed")

        except Exception as e:
            logger.error(f"Error checking skill gate for {skill_path}: {e}")
            return GateResult(can_load=True, message=f"Check failed: {e}")

    async def _parse_metadata(self, metadata_file: Path) -> Optional[SkillMetadata]:
        """解析技能元数据

        Args:
            metadata_file: 元数据文件路径

        Returns:
            Optional[SkillMetadata]: 技能元数据
        """
        if not YAML_AVAILABLE:
            logger.warning("PyYAML not available, skipping metadata parse")
            return None

        try:
            content = metadata_file.read_text(encoding="utf-8")

            # 解析 YAML frontmatter
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    yaml_content = parts[1].strip()
                    data = yaml.safe_load(yaml_content)

                    if data:
                        return SkillMetadata(
                            name=data.get("name", metadata_file.parent.name),
                            version=data.get("version", "1.0.0"),
                            description=data.get("description", ""),
                            requires=data.get("requires", {}),
                            platforms=data.get("platforms", []),
                            platforms_exclude=data.get("platforms_exclude", []),
                            entry=data.get("entry", "skill.py"),
                            dependencies=data.get("dependencies", []),
                            metadata=data
                        )

            # 尝试直接解析 YAML
            data = yaml.safe_load(content)
            if data:
                return SkillMetadata(
                    name=data.get("name", metadata_file.parent.name),
                    version=data.get("version", "1.0.0"),
                    description=data.get("description", ""),
                    requires=data.get("requires", {}),
                    platforms=data.get("platforms", []),
                    platforms_exclude=data.get("platforms_exclude", []),
                    entry=data.get("entry", "skill.py"),
                    dependencies=data.get("dependencies", []),
                    metadata=data
                )

        except Exception as e:
            logger.warning(f"Failed to parse metadata from {metadata_file}: {e}")

        return None

    async def _check_binaries(self, binaries: List[str]) -> List[str]:
        """检查二进制依赖

        Args:
            binaries: 二进制名称列表

        Returns:
            List[str]: 缺失的二进制列表
        """
        missing = []

        for binary in binaries:
            # 缓存检查
            if binary in self._binary_cache:
                if not self._binary_cache[binary]:
                    missing.append(f"binary:{binary}")
                continue

            # 检查二进制是否存在
            found = shutil.which(binary) is not None
            self._binary_cache[binary] = found

            if not found:
                missing.append(f"binary:{binary}")

        return missing

    async def _check_env_vars(self, env_vars: List[str]) -> List[str]:
        """检查环境变量

        Args:
            env_vars: 环境变量名称列表

        Returns:
            List[str]: 缺失的环境变量列表
        """
        missing = []

        for var in env_vars:
            if not os.environ.get(var):
                missing.append(f"env:{var}")

        return missing

    async def _check_configs(self, configs: List[str]) -> List[str]:
        """检查配置文件

        Args:
            configs: 配置项列表 (格式: "section.key")

        Returns:
            List[str]: 缺失的配置项列表
        """
        missing = []

        for config in configs:
            # 配置格式: "section.key" 或 "key"
            parts = config.split(".")

            # 从环境变量或配置文件读取
            env_key = f"{parts[0].upper()}_{'_'.join(parts[1:])}"
            if not os.environ.get(env_key):
                # 尝试读取配置文件
                config_path = Path(f"config/{parts[0]}.yaml")
                if not config_path.exists():
                    missing.append(f"config:{config}")

        return missing

    def _check_platform(
        self,
        platforms: List[str],
        platforms_exclude: List[str]
    ) -> bool:
        """检查平台兼容性

        Args:
            platforms: 支持的平台列表
            platforms_exclude: 排除的平台列表

        Returns:
            bool: 是否兼容
        """
        current_platform = platform.system().lower()

        # 检查排除列表
        if current_platform in [p.lower() for p in platforms_exclude]:
            return False

        # 检查支持列表
        if platforms:
            return current_platform in [p.lower() for p in platforms]

        # 没有指定平台，默认支持
        return True

    def clear_cache(self):
        """清除二进制缓存"""
        self._binary_cache.clear()


# ==================== 便捷函数 ====================

async def check_skill(skill_path: Path) -> GateResult:
    """检查技能

    Args:
        skill_path: 技能目录

    Returns:
        GateResult: 检查结果
    """
    gate = SkillGate()
    return await gate.check(skill_path)


def create_skill_metadata(
    name: str,
    version: str = "1.0.0",
    description: str = "",
    binaries: Optional[List[str]] = None,
    env_vars: Optional[List[str]] = None,
    configs: Optional[List[str]] = None,
    platforms: Optional[List[str]] = None
) -> str:
    """生成技能元数据 YAML

    Args:
        name: 技能名称
        version: 版本
        description: 描述
        binaries: 二进制依赖
        env_vars: 环境变量
        configs: 配置项
        platforms: 支持平台

    Returns:
        str: YAML 内容
    """
    requires = {}
    if binaries:
        requires["binary"] = binaries
    if env_vars:
        requires["env"] = env_vars
    if configs:
        requires["config"] = configs

    data = {
        "name": name,
        "version": version,
        "description": description,
        "requires": requires,
    }

    if platforms:
        data["platforms"] = platforms

    if YAML_AVAILABLE:
        return yaml.dump(data, default_flow_style=False)
    else:
        # 手动生成简单 YAML
        lines = [f"name: {name}", f"version: {version}", f"description: {description}"]
        if requires:
            lines.append("requires:")
            for key, value in requires.items():
                lines.append(f"  {key}: {value}")
        if platforms:
            lines.append(f"platforms: {', '.join(platforms)}")
        return "\n".join(lines)


# ==================== 测试 ====================

if __name__ == "__main__":
    async def test():
        # 创建测试目录
        test_dir = Path("/tmp/test_skill")
        test_dir.mkdir(exist_ok=True)

        # 创建 SKILL.md
        skill_md = test_dir / "SKILL.md"
        skill_md.write_text("""---
name: test_skill
version: "1.0.0"
description: Test skill
requires:
  binary: ["ls", "fake_binary"]
  env: ["FAKE_ENV_VAR"]
platforms: ["darwin", "linux"]
---
""")

        # 检查
        gate = SkillGate()
        result = await gate.check(test_dir)

        print(f"Can load: {result.can_load}")
        print(f"Missing: {result.missing_requirements}")
        print(f"Message: {result.message}")

    asyncio.run(test())

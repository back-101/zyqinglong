#!/usr/bin/env python3
import os
import yaml
import requests
import subprocess
import shutil
import fnmatch
from pathlib import Path
import tempfile

class RepositorySync:
    def __init__(self, config_path):
        self.config_path = config_path
        self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        print(f"📁 加载了 {len(self.config['repositories'])} 个仓库配置")
    
    def download_file(self, repo_url, file_path, target_path, branch="main"):
        """下载单个文件 - 支持 GitHub 和 Gitee"""
        try:
            if 'github.com' in repo_url:
                # GitHub 处理
                raw_url = repo_url.replace('https://github.com/', 'https://raw.githubusercontent.com/')
                raw_url = f"{raw_url}/{branch}/{file_path}"
                print(f"  📥 GitHub 下载: {raw_url}")
                
            elif 'gitee.com' in repo_url:
                # Gitee 处理
                parts = repo_url.replace('https://gitee.com/', '').split('/')
                if len(parts) >= 2:
                    user = parts[0]
                    repo = parts[1]
                    raw_url = f"https://gitee.com/{user}/{repo}/raw/{branch}/{file_path}"
                    print(f"  📥 Gitee 下载: {raw_url}")
                else:
                    raise ValueError(f"无效的 Gitee URL: {repo_url}")
            else:
                raise ValueError("暂不支持此代码托管平台")
            
            response = requests.get(raw_url, timeout=30)
            response.raise_for_status()
            
            # 确保目标目录存在
            Path(target_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(target_path, 'wb') as f:
                f.write(response.content)
            
            print(f"  ✅ 成功: {file_path}")
            return True
            
        except Exception as e:
            print(f"  ❌ 下载失败 {file_path}: {e}")
            return False
    
    def should_include_path(self, relative_path, include_patterns, exclude_patterns):
        """判断路径是否应该包含"""
        relative_str = str(relative_path)
        
        # 如果没有包含规则，默认包含所有
        if not include_patterns:
            include_patterns = ['*']
        
        # 检查是否匹配任何包含模式
        included = any(
            fnmatch.fnmatch(relative_str, include_pattern) 
            for include_pattern in include_patterns
        )
        
        # 检查是否匹配任何排除模式
        excluded = any(
            fnmatch.fnmatch(relative_str, exclude_pattern) 
            for exclude_pattern in exclude_patterns
        )
        
        # 检查路径的任何部分是否是完全匹配的排除项（用于文件夹排除）
        path_parts = relative_str.split('/')
        folder_excluded = any(
            excluded in path_parts 
            for excluded in exclude_patterns 
            if '/' not in excluded and '*' not in excluded and '?' not in excluded and '[' not in excluded
        )
        
        return included and not excluded and not folder_excluded
    
    def clone_and_filter_files(self, repo_config, target_dir):
        """使用克隆方式获取文件，支持排除文件和文件夹"""
        repo_url = repo_config['source']
        branch = repo_config.get('branch', 'main')
        
        # 获取规则
        include_files = []
        exclude_files = []
        for rule in repo_config.get('rules', []):
            if rule['type'] == 'include':
                include_files.extend(rule['patterns'])
            elif rule['type'] == 'exclude':
                exclude_files.extend(rule['patterns'])
        
        temp_dir = tempfile.mkdtemp()
        
        try:
            print(f"  📥 克隆仓库: {repo_url}")
            result = subprocess.run([
                'git', 'clone', '--depth', '1',
                '--branch', branch, repo_url, temp_dir
            ], capture_output=True, text=True, encoding='utf-8')
            
            if result.returncode != 0:
                print(f"  ❌ 克隆失败: {result.stderr}")
                return False
            
            # 查找并复制文件
            copied_count = 0
            for file_path in Path(temp_dir).rglob('*'):
                if file_path.is_file() and '.git' not in str(file_path):
                    relative_path = file_path.relative_to(Path(temp_dir))
                    
                    if self.should_include_path(relative_path, include_files, exclude_files):
                        target_file = Path(target_dir) / file_path.name
                        shutil.copy2(file_path, target_file)
                        print(f"  📄 复制: {file_path.name}")
                        copied_count += 1
                    else:
                        print(f"  🚫 排除: {relative_path}")
            
            print(f"  📊 结果: 复制了 {copied_count} 个文件")
            return copied_count > 0
            
        except Exception as e:
            print(f"  ❌ 克隆同步失败: {e}")
            return False
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def sync_repository(self, repo_name, repo_config):
        """同步单个仓库"""
        print(f"\n🔧 同步仓库: {repo_name}")
        print(f"  源仓库: {repo_config['source']}")
        
        target_dir = repo_config['target_dir']
        if target_dir == ".":
            target_path = Path(".")
        else:
            target_path = Path(target_dir)
            target_path.mkdir(parents=True, exist_ok=True)
        
        # 显示排除规则
        exclude_rules = []
        for rule in repo_config.get('rules', []):
            if rule['type'] == 'exclude':
                exclude_rules.extend(rule['patterns'])
        if exclude_rules:
            print(f"  排除规则: {exclude_rules}")
        
        # 对于 Gitee 仓库，优先使用克隆方式
        if 'gitee.com' in repo_config['source']:
            print("  🔄 对 Gitee 仓库使用克隆方式")
            return self.clone_and_filter_files(repo_config, target_path)
        
        # 检查是否只需要下载单个文件
        rules = repo_config.get('rules', [])
        include_rules = [r for r in rules if r['type'] == 'include']
        
        # 如果只有包含规则且都是具体文件，使用直接下载
        if (len(rules) == 1 and rules[0]['type'] == 'include' and
            all('*' not in pattern and '?' not in pattern and '[' not in pattern 
                for pattern in rules[0]['patterns'])):
            
            print("  🎯 使用直接下载模式")
            success_count = 0
            for pattern in rules[0]['patterns']:
                if target_dir == ".":
                    target_file = Path(Path(pattern).name)
                else:
                    target_file = target_path / Path(pattern).name
                    
                if self.download_file(repo_config['source'], pattern, target_file, 
                                    repo_config.get('branch', 'main')):
                    success_count += 1
            
            # 如果直接下载失败，尝试克隆方式
            if success_count == 0:
                print("  🔄 直接下载失败，尝试克隆方式")
                return self.clone_and_filter_files(repo_config, target_path)
            
            print(f"  📊 结果: {success_count}/{len(rules[0]['patterns'])} 个文件下载成功")
            return success_count > 0
        
        else:
            # 使用克隆+过滤模式
            print("  🔄 使用克隆+过滤模式")
            return self.clone_and_filter_files(repo_config, target_path)
    
    def sync_all(self):
        """同步所有配置的仓库"""
        print("🚀 开始同步所有仓库...")
        
        results = {}
        for repo_name, repo_config in self.config['repositories'].items():
            try:
                success = self.sync_repository(repo_name, repo_config)
                results[repo_name] = success
            except Exception as e:
                print(f"  💥 同步 {repo_name} 时出错: {e}")
                results[repo_name] = False
        
        # 输出总结
        print("\n" + "="*50)
        print("📈 同步总结:")
        for repo_name, success in results.items():
            status = "✅ 成功" if success else "❌ 失败"
            print(f"  {repo_name}: {status}")
        
        success_count = sum(1 for s in results.values() if s)
        print(f"\n总览: {success_count}/{len(results)} 个仓库同步成功")
        
        return all(results.values())

if __name__ == "__main__":
    config_path = ".github/sync-rules.yaml"
    sync_manager = RepositorySync(config_path)
    sync_manager.sync_all()

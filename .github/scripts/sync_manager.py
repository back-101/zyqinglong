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
        self.config = {}
        self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        if not os.path.exists(self.config_path):
            print(f"❌ 错误: 找不到配置文件 {self.config_path}")
            exit(1)
            
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        # 检查必要的键是否存在
        if 'repositories' not in self.config:
            print("❌ 错误: 配置文件中缺少 'repositories' 键，请检查 YAML 格式！")
            exit(1)
            
        print(f"📁 加载了 {len(self.config['repositories'])} 个仓库配置")
    
    def download_file(self, repo_url, file_path, target_path, branch="main"):
        """下载单个文件 - 支持 GitHub 和 Gitee"""
        try:
            if 'github.com' in repo_url:
                raw_url = repo_url.replace('https://github.com/', 'https://raw.githubusercontent.com/')
                raw_url = f"{raw_url}/{branch}/{file_path}"
                print(f"  📥 GitHub 下载: {raw_url}")
            elif 'gitee.com' in repo_url:
                parts = repo_url.replace('https://gitee.com/', '').split('/')
                if len(parts) >= 2:
                    user, repo = parts[0], parts[1]
                    raw_url = f"https://gitee.com/{user}/{repo}/raw/{branch}/{file_path}"
                    print(f"  📥 Gitee 下载: {raw_url}")
                else:
                    raise ValueError(f"无效的 Gitee URL: {repo_url}")
            else:
                raise ValueError("暂不支持此代码托管平台")
            
            response = requests.get(raw_url, timeout=30)
            response.raise_for_status()
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
        if not include_patterns:
            include_patterns = ['*']
        
        included = any(fnmatch.fnmatch(relative_str, p) for p in include_patterns)
        excluded = any(fnmatch.fnmatch(relative_str, p) for p in exclude_patterns)
        
        path_parts = relative_str.split('/')
        folder_excluded = any(
            ex in path_parts for ex in exclude_patterns 
            if '/' not in ex and '*' not in ex
        )
        return included and not excluded and not folder_excluded

    def clone_and_filter_files(self, repo_config, target_dir):
        """使用克隆方式获取文件"""
        repo_url = repo_config['source']
        branch = repo_config.get('branch', 'main')
        include_files = []
        exclude_files = []
        
        for rule in repo_config.get('rules', []):
            if rule['type'] == 'include':
                include_files.extend(rule['patterns'])
            elif rule['type'] == 'exclude':
                exclude_files.extend(rule['patterns'])
        
        temp_dir = tempfile.mkdtemp()
        try:
            print(f"  📥 克隆仓库: {repo_url} (分支: {branch})")
            result = subprocess.run([
                'git', 'clone', '--depth', '1', '--branch', branch, repo_url, temp_dir
            ], capture_output=True, text=True, encoding='utf-8')
            
            if result.returncode != 0:
                print(f"  ❌ 克隆失败: {result.stderr}")
                return False
            
            copied_count = 0
            for file_path in Path(temp_dir).rglob('*'):
                if file_path.is_file() and '.git' not in str(file_path):
                    relative_path = file_path.relative_to(Path(temp_dir))
                    if self.should_include_path(relative_path, include_files, exclude_files):
                        target_file = Path(target_dir) / file_path.name
                        shutil.copy2(file_path, target_file)
                        copied_count += 1
            
            print(f"  📊 结果: 复制了 {copied_count} 个文件")
            return copied_count > 0
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def sync_repository(self, repo_name, repo_config):
        """同步单个仓库"""
        print(f"\n🔧 同步仓库: {repo_name}")
        target_dir = repo_config.get('target_dir', '.')
        target_path = Path(target_dir)
        target_path.mkdir(parents=True, exist_ok=True)
        
        if 'gitee.com' in repo_config['source']:
            return self.clone_and_filter_files(repo_config, target_path)
        
        # 默认尝试克隆+过滤模式，因为它最稳妥
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
        
        print("\n" + "="*50 + "\n📈 同步总结:")
        for name, res in results.items():
            print(f"  {name}: {'✅ 成功' if res else '❌ 失败'}")
        
        return all(results.values())

if __name__ == "__main__":
    config_path = ".github/sync-rules.yaml"
    sync_manager = RepositorySync(config_path)
    sync_manager.sync_all()

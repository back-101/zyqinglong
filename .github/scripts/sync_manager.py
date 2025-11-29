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
            elif 'gitee.com' in repo_url:
                # Gitee 处理
                # Gitee 的 raw 地址格式: https://gitee.com/用户名/仓库/raw/分支/文件路径
                raw_url = repo_url.replace('https://gitee.com/', 'https://gitee.com/')
                raw_url = f"{raw_url}/raw/{branch}/{file_path}"
            else:
                raise ValueError("暂不支持此代码托管平台")
            
            print(f"  📥 下载: {raw_url}")
            
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
    
    def clone_and_filter(self, repo_config, temp_dir):
        """克隆仓库并根据规则过滤文件 - 支持 GitHub 和 Gitee"""
        repo_url = repo_config['source']
        repo_name = repo_url.split('/')[-1]
        repo_dir = Path(temp_dir) / repo_name
        
        try:
            # 克隆仓库（浅克隆）
            print(f"  📥 克隆仓库: {repo_url}")
            subprocess.run([
                'git', 'clone', '--depth', '1',
                '--branch', repo_config.get('branch', 'main'),
                repo_url, str(repo_dir)
            ], check=True, capture_output=True)
            
            return repo_dir
            
        except subprocess.CalledProcessError as e:
            print(f"  ❌ 克隆失败: {e}")
            # 输出详细错误信息
            print(f"  错误输出: {e.stderr.decode() if e.stderr else '无输出'}")
            return None
    
    def should_include_file(self, file_path, rules, repo_name):
        """根据规则判断文件是否应该包含"""
        file_path = str(file_path)
        include_files = []
        exclude_files = []
        
        # 分类规则
        for rule in rules:
            if rule['type'] == 'include':
                include_files.extend(rule['patterns'])
            elif rule['type'] == 'exclude':
                exclude_files.extend(rule['patterns'])
        
        # 如果没有包含规则，默认包含所有
        if not include_files:
            include_files = ['*']
        
        # 检查是否匹配任何包含模式
        included = any(fnmatch.fnmatch(file_path, pattern) for pattern in include_files)
        
        # 检查是否匹配任何排除模式
        excluded = any(fnmatch.fnmatch(file_path, pattern) for pattern in exclude_files)
        
        # 永远排除 .git 目录
        if '.git' in file_path:
            return False
            
        return included and not excluded
    
    def copy_filtered_files(self, source_dir, target_dir, rules, repo_name):
        """复制过滤后的文件"""
        source_path = Path(source_dir)
        target_path = Path(target_dir)
        
        copied_count = 0
        
        for file_path in source_path.rglob('*'):
            if file_path.is_file():
                relative_path = file_path.relative_to(source_path)
                
                if self.should_include_file(relative_path, rules, repo_name):
                    # 如果目标目录是根目录，直接使用文件名
                    if str(target_path) == ".":
                        target_file = Path(relative_path.name)
                    else:
                        target_file = target_path / relative_path
                    
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file_path, target_file)
                    print(f"  📄 复制: {relative_path} -> {target_file}")
                    copied_count += 1
        
        return copied_count
    
    def sync_repository(self, repo_name, repo_config):
        """同步单个仓库"""
        print(f"\n🔧 同步仓库: {repo_name}")
        
        target_dir = repo_config['target_dir']
        if target_dir == ".":
            target_path = Path(".")
        else:
            target_path = Path(target_dir)
            target_path.mkdir(parents=True, exist_ok=True)
        
        # 检查是否只需要下载单个文件
        rules = repo_config.get('rules', [])
        include_rules = [r for r in rules if r['type'] == 'include']
        
        # 如果只有包含规则且都是具体文件（没有通配符），使用直接下载
        if (len(rules) == 1 and rules[0]['type'] == 'include' and
            all('*' not in pattern and '?' not in pattern and '[' not in pattern 
                for pattern in rules[0]['patterns'])):
            
            print("  🎯 使用直接下载模式（单个文件）")
            success_count = 0
            for pattern in rules[0]['patterns']:
                # 根目录下直接使用文件名
                if target_dir == ".":
                    target_file = Path(Path(pattern).name)
                else:
                    target_file = target_path / Path(pattern).name
                    
                if self.download_file(repo_config['source'], pattern, target_file, 
                                    repo_config.get('branch', 'main')):
                    success_count += 1
            
            print(f"  📊 结果: {success_count}/{len(rules[0]['patterns'])} 个文件下载成功")
            return success_count > 0
        
        else:
            # 使用克隆+过滤模式
            print("  🔄 使用克隆+过滤模式")
            with tempfile.TemporaryDirectory() as temp_dir:
                repo_dir = self.clone_and_filter(repo_config, temp_dir)
                if not repo_dir:
                    return False
                
                copied_count = self.copy_filtered_files(repo_dir, target_path, rules, repo_name)
                print(f"  📊 结果: 复制了 {copied_count} 个文件")
                return copied_count > 0
    
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

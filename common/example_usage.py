"""
工厂模式AI测试器使用示例
"""
import os
from aiFactory.factory import AIProviderFactory, AIProviderType

def main():
    """主函数 - 演示如何使用AI提供者工厂"""
    
    print("="*60)
    print("AI API测试器 - 工厂模式实现")
    print("="*60)
    
    # 示例1: 创建通义千问测试器
    print("\n【示例1】创建通义千问测试器")
    try:
        # 从环境变量获取API密钥（实际使用时替换为真实密钥）
        api_key = os.getenv("QWEN_API_KEY", "sk-f220dff5e50b4a46bc1757c04bf5539d")
        qwen_tester = AIProviderFactory.create_provider(
            AIProviderType.QWEN,
            api_key=api_key
        )
        
        print("✓ 成功创建Qwen测试器")
        
        # 测试基本功能
        print("\n测试模型列表...")
        models = qwen_tester.list_models(verbose=False)
        print(f"找到 {len(models)} 个模型")
        
        # 简单聊天测试
        print("\n测试聊天功能...")
        response = qwen_tester.chat_completion(
            prompt="请用中文简单介绍你自己",
            max_length=100
        )
        if response:
            print("✓ 聊天功能正常")
        else:
            print("✗ 聊天功能异常（可能是API密钥无效）")
            
    except Exception as e:
        print(f"✗ 创建Qwen测试器失败: {e}")
    
    # 示例2: 创建Ollama测试器
    print("\n【示例2】创建Ollama测试器")
    try:
        ollama_tester = AIProviderFactory.create_provider(
            AIProviderType.OLLAMA,
            base_url="http://localhost:11434"
        )
        
        print("✓ 成功创建Ollama测试器")
        
        # 测试服务健康状态
        print("\n测试服务健康状态...")
        is_healthy = ollama_tester.check_health()
        if is_healthy:
            print("✓ Ollama服务正常运行")
        else:
            print("✗ Ollama服务未运行或无法连接")
        
        # 测试模型列表
        if is_healthy:
            print("\n测试模型列表...")
            models = ollama_tester.list_models(verbose=False)
            print(f"找到 {len(models)} 个模型")
        
    except Exception as e:
        print(f"✗ 创建Ollama测试器失败: {e}")
    
    # 示例3: 使用工厂方法动态创建
    print("\n【示例3】动态创建不同类型的测试器")
    
    providers_config = [
        {"type": AIProviderType.QWEN, "config": {"api_key": "sk-f220dff5e50b4a46bc1757c04bf5539d"}},
        {"type": AIProviderType.OLLAMA, "config": {"base_url": "http://localhost:11434"}}
    ]
    
    for i, config in enumerate(providers_config, 1):
        try:
            provider = AIProviderFactory.create_provider(config["type"], **config["config"])
            print(f"✓ 第{i}个测试器创建成功: {type(provider).__name__}")
            print(f"✓ 第{i}个测试器创建成功: {provider.list_models()}")
        except Exception as e:
            print(f"✗ 第{i}个测试器创建失败: {e}")
    
    print("\n" + "="*60)
    print("工厂模式AI测试器演示完成")
    print("="*60)


if __name__ == "__main__":
    main()
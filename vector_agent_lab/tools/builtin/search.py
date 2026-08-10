"""Search tool.

Planned responsibility:
- connect Agent workflows to external search or retrieval systems
- start as a mock/search-interface example before real backends are added
"""

# my_advanced_search.py
import os
from typing import Optional, List, Dict, Any
from ..registry import ToolRegistry

class MyAdvancedSearchTool:
    """
    自定义高级搜索工具类
    展示多源整合和智能选择的设计模式
    """

    def __init__(self):
        self.name = "my_advanced_search"
        self.description = "智能搜索工具，支持 Tavily 和 SerpAPI 多个搜索源，返回摘要、标题、链接和片段"
        self.search_sources = []
        self._setup_search_sources()

    def _setup_search_sources(self):
        """设置可用的搜索源"""
        # 检查Tavily可用性
        if os.getenv("TAVILY_API_KEY"):
            try:
                from tavily import TavilyClient
                self.tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
                self.search_sources.append("tavily")
                print("✅ Tavily搜索源已启用")
            except ImportError:
                print("⚠️ Tavily库未安装")

        # 检查SerpApi可用性
        if os.getenv("SERPAPI_API_KEY"):
            try:
                import serpapi
                self.search_sources.append("serpapi")
                print("✅ SerpApi搜索源已启用")
            except ImportError:
                print("⚠️ SerpApi库未安装")

        if self.search_sources:
            print(f"🔧 可用搜索源: {', '.join(self.search_sources)}")
        else:
            print("⚠️ 没有可用的搜索源，请配置API密钥")

    def search(self, query: str) -> str:
        """执行智能搜索"""
        if not query.strip():
            return "❌ 错误:搜索查询不能为空"

        # 检查是否有可用的搜索源
        if not self.search_sources:
            return """❌ 没有可用的搜索源，请配置以下API密钥之一:

1. Tavily API: 设置环境变量 TAVILY_API_KEY
   获取地址: https://tavily.com/

2. SerpAPI: 设置环境变量 SERPAPI_API_KEY
   获取地址: https://serpapi.com/

配置后重新运行程序。"""

        print(f"🔍 开始智能搜索: {query}")

        # 尝试多个搜索源，并合并可用结果
        successful_results = []
        for source in self.search_sources:
            try:
                if source == "tavily":
                    result = self._search_with_tavily(query)
                    if result and "未找到" not in result:
                        successful_results.append(f"📊 Tavily AI搜索结果:\n\n{result}")

                elif source == "serpapi":
                    result = self._search_with_serpapi(query)
                    if result and "未找到" not in result:
                        successful_results.append(f"🌐 SerpApi Google搜索结果:\n\n{result}")

            except Exception as e:
                print(f"⚠️ {source} 搜索失败: {e}")
                continue

        if successful_results:
            return "\n\n---\n\n".join(successful_results)

        return "❌ 所有搜索源都失败了，请检查网络连接和API密钥配置"

    def _search_with_tavily(self, query: str) -> str:
        """使用Tavily搜索"""
        try:
            response = self.tavily_client.search(
                query=query,
                max_results=5,
                search_depth="advanced",
                include_answer=True,
            )
        except TypeError:
            response = self.tavily_client.search(query=query, max_results=5)

        if response.get('answer'):
            result = f"💡 AI直接答案:{response['answer']}\n\n"
        else:
            result = ""

        results = response.get('results', [])[:5]
        if not result and not results:
            return "未找到相关结果"

        result += "🔗 相关结果:\n"
        for i, item in enumerate(results, 1):
            result += f"[{i}] {item.get('title', '')}\n"
            if item.get("url"):
                result += f"    URL: {item.get('url')}\n"
            if item.get("published_date"):
                result += f"    Published: {item.get('published_date')}\n"
            result += f"    {item.get('content', '')[:300]}...\n\n"

        return result

    def _search_with_serpapi(self, query: str) -> str:
        """使用SerpApi搜索"""
        import serpapi

        search = serpapi.GoogleSearch({
            "q": query,
            "api_key": os.getenv("SERPAPI_API_KEY"),
            "num": 5
        })

        results = search.get_dict()

        result = "🔗 Google搜索结果:\n"
        if "organic_results" in results:
            organic_results = results["organic_results"][:5]
            if not organic_results:
                return "未找到相关结果"

            for i, res in enumerate(organic_results, 1):
                result += f"[{i}] {res.get('title', '')}\n"
                if res.get("link"):
                    result += f"    URL: {res.get('link')}\n"
                if res.get("date"):
                    result += f"    Date: {res.get('date')}\n"
                result += f"    {res.get('snippet', '')}\n\n"
        else:
            return "未找到相关结果"

        return result

def create_advanced_search_registry():
    """创建包含高级搜索工具的注册表"""
    registry = ToolRegistry()

    # 创建搜索工具实例
    search_tool = MyAdvancedSearchTool()

    # 注册搜索工具的方法作为函数
    registry.register_function(
        name="advanced_search",
        description=(
            "高级搜索工具，适合搜索最新、实时、新闻、天气、政策、疫情、病毒、公共卫生、价格等动态网页信息。"
            "输入应是搜索关键词；公共卫生问题建议包含“官方、疾控、通报、监测”等限定词。"
        ),
        func=search_tool.search
    )

    return registry

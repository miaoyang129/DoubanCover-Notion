import os
import requests
from bs4 import BeautifulSoup
from notion_client import Client
import time

# 从环境变量获取 Token 和 Database ID
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("DATABASE_ID")

if not NOTION_TOKEN or not DATABASE_ID:
    raise ValueError("请确保在环境变量中设置了 NOTION_TOKEN 和 DATABASE_ID")

notion = Client(auth=NOTION_TOKEN)

def get_douban_cover(url):
    """从豆瓣 URL 抓取封面图片链接"""
    # 必须伪装 User-Agent，否则豆瓣会直接拒绝请求 (403)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 豆瓣书籍和电影的封面通常在一个 id 为 'mainpic' 的 div 下的 img 标签中
        mainpic_div = soup.find('div', id='mainpic')
        if mainpic_div:
            img_tag = mainpic_div.find('img')
            if img_tag and 'src' in img_tag.attrs:
                return img_tag['src']
    except Exception as e:
        print(f"抓取失败 {url}: {e}")
    return None

def update_notion_cover():
    """查询数据库并更新封面"""
    # 1. 查询需要更新的页面
    # 这里假设你的 URL 属性名叫做 "Link"，你需要根据实际情况修改
    query = notion.databases.query(
        **{
            "database_id": database_id,
            "filter": {
                "and": [
                    {
                        "property": "Link",
                        "url": {"is_not_empty": True}
                    }
                    # 可以在这里进一步添加过滤条件，比如只筛选 Cover 为空的条目
                ]
            }
        }
    )

    pages = query.get('results')

    for page in pages:
        page_id = page['id']
        # 提取 URL
        try:
            douban_url = page['properties']['Link']['url']
            if 'douban.com' not in douban_url:
                continue
        except KeyError:
            continue

        # 2. 获取封面图
        cover_url = get_douban_cover(douban_url)
        
        if cover_url:
            # 3. 更新 Notion 页面
            # Notion API 目前不支持直接上传图片文件，只能使用外部链接 (external url)
            notion.pages.update(
                page_id=page_id,
                cover={
                    "type": "external",
                    "external": {
                        "url": cover_url
                    }
                }
            )
            print(f"成功更新页面 {page_id} 的封面: {cover_url}")
            # 增加延时，防止触发豆瓣或 Notion 的速率限制
            time.sleep(2)

if __name__ == "__main__":
    update_notion_cover()

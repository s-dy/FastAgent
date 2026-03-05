from typing import Annotated
from pydantic import Field
from fastmcp import FastMCP
from crawler import Crawler

mcp = FastMCP(name="HotelMCP", version="1.0.0")

@mcp.tool(name='search_hotels', timeout=120)
def search_hotels(
    prefix_query: Annotated[str, Field(description="城市地区，例如：北京、杭州、北京朝阳区、上海")],
    checkin: Annotated[str, Field(description="入住日期，格式：2026-01-01")],
    checkout: Annotated[str, Field(description="退房日期，格式：2026-01-02")],
    nb_adults: Annotated[int, Field(description="成人数量")] = 2,
    nb_children: Annotated[int, Field(description="儿童数量")] = 0,
    nb_rooms: Annotated[int, Field(description="房间数量")] = 1,
    offset: Annotated[int, Field(description="分页参数，从25开始，步长为25")] = 25,
) -> list:
    """根据城市地区搜索酒店详情"""
    crawler = Crawler()
    return crawler.search_hotels(prefix_query, checkin, checkout, nb_adults, nb_children, nb_rooms, offset)

if __name__ == '__main__':
    mcp.run(transport="http", host="0.0.0.0", port=8989)
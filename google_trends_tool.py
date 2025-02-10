from pytrends.request import TrendReq
from superagi.tools.base_tool import BaseTool

class GoogleTrendsTool(BaseTool):
    name = "Google Trends Analyzer"
    description = "Fetches trending search topics from Google Trends based on keywords."

    def __init__(self):
        super().__init__()
        self.pytrends = TrendReq(hl='en-US', tz=360)

    def _run(self, keyword: str, timeframe: str = 'now 7-d', geo: str = '', category: int = 0):
        """
        Fetches trending topics for a given keyword.

        Args:
            keyword (str): The keyword to search trends for.
            timeframe (str): Time range for trends (default: 'now 7-d').
            geo (str): Geographical location code (e.g., 'US', 'RU'). Default is worldwide.
            category (int): Category code for more specific searches. Default is 0 (all).

        Returns:
            dict: Trending data for the given keyword.
        """
        try:
            self.pytrends.build_payload([keyword], timeframe=timeframe, geo=geo, cat=category)
            data = self.pytrends.interest_over_time()
            if not data.empty:
                trend_data = data[keyword].to_dict()
                return {
                    "status": "success",
                    "keyword": keyword,
                    "trend_data": trend_data
                }
            else:
                return {
                    "status": "no data",
                    "message": f"No trending data found for '{keyword}'."
                }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def _run_batch(self, keywords: list, timeframe: str = 'now 7-d', geo: str = '', category: int = 0):
        """
        Fetch trends for multiple keywords.

        Args:
            keywords (list): List of keywords to search.

        Returns:
            dict: Trending data for all keywords.
        """
        result = {}
        for keyword in keywords:
            result[keyword] = self._run(keyword, timeframe, geo, category)
        return result

from superagi.tools.base_toolkit import BaseToolkit
from google_trends_tool import GoogleTrendsTool

class GoogleTrendsToolkit(BaseToolkit):
    name = "Google Trends Toolkit"
    description = "Toolkit for fetching and analyzing Google Trends data."
    
    def get_tools(self):
        return [GoogleTrendsTool()]
    
    def get_env_keys(self):
        """
        Returns environment variables required for the toolkit.
        For pytrends, no API key is required, but you can add proxy or region settings here.
        """
        return []

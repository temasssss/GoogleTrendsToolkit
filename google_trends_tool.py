import os
from superagi.tools.base_tool import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Optional
from superagi.resource_manager.file_manager import FileManager
from pytrends.request import TrendReq

class GoogleTrendsToolInput(BaseModel):
    keyword: str = Field(..., description="The keyword to search trends for.")
    timeframe: str = Field(default='now 7-d', description="Time range for trends (e.g., 'now 7-d', 'today 12-m').")
    geo: str = Field(default='', description="Geographical location code (e.g., 'US', 'RU'). Leave empty for worldwide trends.")
    store_report_in_file: bool = Field(default=True, description="True if the report should be stored in a file. False otherwise.")

class GoogleTrendsTool(BaseTool):
    """
    Google Trends Tool
    """
    name: str = "Google Trends Tool"
    args_schema: Type[BaseModel] = GoogleTrendsToolInput
    description: str = "Fetches trending search topics from Google Trends based on keywords."
    resource_manager: Optional[FileManager] = None

    def _execute(self, keyword: str, timeframe: str, geo: str, store_report_in_file: bool):
        pytrends = TrendReq(hl='en-US', tz=360)
        
        # Построение запроса к Google Trends
        pytrends.build_payload([keyword], timeframe=timeframe, geo=geo)
        data = pytrends.interest_over_time()

        if data.empty:
            return f"No trending data found for '{keyword}'."

        report = self._generate_report(data, keyword)

        # Сохранение отчёта в файл, если указано
        if store_report_in_file:
            filename = f"{keyword.replace(' ', '_')}_trends_report.txt"
            self.resource_manager.write_file(filename, report)
            return f"Successfully wrote report to {filename}."
        
        return report

    def _generate_report(self, data, keyword):
        report = f"Trends Report for '{keyword}':\n\n"
        report += "Date\t\tInterest\n"
        report += "-" * 30 + "\n"
        
        for date, value in data[keyword].items():
            report += f"{date.strftime('%Y-%m-%d')}\t{value}\n"
        
        return report

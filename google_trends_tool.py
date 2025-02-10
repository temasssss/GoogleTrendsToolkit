import os
from superagi.tools.base_tool import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Optional, List
from superagi.resource_manager.file_manager import FileManager
from pytrends.request import TrendReq

class GoogleTrendsToolInput(BaseModel):
    keywords: List[str] = Field(..., description="List of keywords to search trends for.")
    timeframe: str = Field(default='now 7-d', description="Time range for trends (e.g., 'now 7-d', 'today 12-m').")
    geo: str = Field(default='', description="Geographical location code (e.g., 'US', 'RU'). Leave empty for worldwide trends.")
    store_report_in_file: bool = Field(default=True, description="True if the report should be stored in a file. False otherwise.")
    include_related_queries: bool = Field(default=True, description="Include related and rising queries in the report.")
    include_geo_analysis: bool = Field(default=True, description="Include geographical analysis in the report.")
    include_seasonality: bool = Field(default=True, description="Include seasonality analysis in the report.")

class GoogleTrendsTool(BaseTool):
    """
    Google Trends Tool with extended functionalities.
    """
    name: str = "Google Trends Tool"
    args_schema: Type[BaseModel] = GoogleTrendsToolInput
    description: str = "Fetches trending search topics from Google Trends, compares keywords, includes related queries, and provides geographical and seasonal analysis."
    resource_manager: Optional[FileManager] = None

    def _execute(self, keywords: List[str], timeframe: str, geo: str, store_report_in_file: bool, include_related_queries: bool, include_geo_analysis: bool, include_seasonality: bool):
        pytrends = TrendReq(hl='en-US', tz=360)
        
        # Построение запроса к Google Trends с несколькими ключевыми словами
        pytrends.build_payload(keywords, timeframe=timeframe, geo=geo)
        data = pytrends.interest_over_time()

        if data.empty:
            return f"No trending data found for {', '.join(keywords)}."

        report = self._generate_trend_report(data, keywords)

        # Анализ связанных запросов
        if include_related_queries:
            related_queries = pytrends.related_queries()
            report += self._generate_related_queries_report(related_queries, keywords)

        # Географический анализ
        if include_geo_analysis:
            geo_data = pytrends.interest_by_region(resolution='CITY', geo=geo)
            report += self._generate_geo_report(geo_data)

        # Анализ сезонности
        if include_seasonality:
            seasonality_data = self._analyze_seasonality(pytrends, keywords, geo)
            report += self._generate_seasonality_report(seasonality_data, keywords)

        # Сохранение отчёта в файл, если указано
        if store_report_in_file:
            filename = f"{'_'.join([k.replace(' ', '_') for k in keywords])}_trends_report.txt"
            self.resource_manager.write_file(filename, report)
            return f"Successfully wrote report to {filename}."
        
        return report

    def _generate_trend_report(self, data, keywords):
        report = f"Trends Report for: {', '.join(keywords)}\n\n"
        report += "Date\t\t" + "\t".join(keywords) + "\n"
        report += "-" * (20 + len(keywords) * 10) + "\n"

        for date, row in data.iterrows():
            values = "\t".join(str(row[key]) for key in keywords)
            report += f"{date.strftime('%Y-%m-%d')}\t{values}\n"

        report += "\n"
        return report

    def _generate_related_queries_report(self, related_queries, keywords):
        report = "\nRelated Queries:\n"
        report += "-" * 30 + "\n"

        for keyword in keywords:
            if keyword in related_queries:
                top_queries = related_queries[keyword]['top']
                rising_queries = related_queries[keyword]['rising']

                if top_queries is not None:
                    report += f"Top Related Queries for '{keyword}':\n"
                    for _, row in top_queries.iterrows():
                        report += f"{row['query']} - {row['value']}\n"
                else:
                    report += f"No top related queries found for '{keyword}'.\n"

                if rising_queries is not None:
                    report += f"\nRising Queries for '{keyword}':\n"
                    for _, row in rising_queries.iterrows():
                        report += f"{row['query']} - {row['value']}\n"
                else:
                    report += f"No rising queries found for '{keyword}'.\n"
            else:
                report += f"No related queries data available for '{keyword}'.\n"

            report += "\n"
        return report

    def _generate_geo_report(self, geo_data):
        report = "\nGeographical Analysis:\n"
        report += "-" * 30 + "\n"

        if geo_data.empty:
            return "No geographical data available.\n"

        geo_data_sorted = geo_data.sort_values(by=geo_data.columns[0], ascending=False).head(10)
        for region, row in geo_data_sorted.iterrows():
            report += f"{region} - {row.values[0]}\n"

        report += "\n"
        return report

    def _analyze_seasonality(self, pytrends, keywords, geo):
        pytrends.build_payload(keywords, timeframe='all', geo=geo)
        seasonality_data = pytrends.interest_over_time()
        return seasonality_data

    def _generate_seasonality_report(self, seasonality_data, keywords):
        report = "\nSeasonality Analysis:\n"
        report += "-" * 30 + "\n"

        if seasonality_data.empty:
            return "No seasonality data available.\n"

        for keyword in keywords:
            report += f"\nSeasonality for '{keyword}':\n"
            max_interest = seasonality_data[keyword].max()
            peak_dates = seasonality_data[seasonality_data[keyword] == max_interest].index

            for date in peak_dates:
                report += f"Peak interest on {date.strftime('%Y-%m-%d')} with value {max_interest}\n"

        report += "\n"
        return report

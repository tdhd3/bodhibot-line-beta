import logging
from typing import List, Dict, Any, Optional
import random

from app.services.sutra_retriever import sutra_retriever

# 配置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SutraRecommender:
    """經典推薦服務"""
    
    def __init__(self):
        """初始化經典推薦服務"""
        self.sutra_retriever = sutra_retriever
        
        # 經典分類映射，用於相關推薦
        self.sutra_categories = {
            "般若類": ["T0235", "T0251", "T0220"],  # 金剛經、心經、大般若經
            "淨土類": ["T0366", "T0360"],  # 阿彌陀經、無量壽經
            "禪宗類": ["T2008", "T2005", "X1001"],  # 六祖壇經、無門關、碧巌錄
            "唯識類": ["T1585", "T1579", "T1586"],  # 成唯識論、瑜伽師地論、唯識三十頌
            "中觀類": ["T1564", "T1568"],  # 中論、十二門論
            "戒律類": ["T1428", "T1484"],  # 四分律、梵網經
            "續藏類": ["T1911", "T1956"],  # 摩訶止觀、天台小止觀
        }
        
        # 經典基本信息
        self.sutra_info = {
            "T0235": {"name": "金剛經", "full_name": "金剛般若波羅蜜經", "length": "短", "difficulty": "中"},
            "T0251": {"name": "心經", "full_name": "般若波羅蜜多心經", "length": "極短", "difficulty": "入門"},
            "T0366": {"name": "阿彌陀經", "full_name": "佛說阿彌陀經", "length": "短", "difficulty": "入門"},
            "T0360": {"name": "無量壽經", "full_name": "佛說無量壽經", "length": "中", "difficulty": "中"},
            "T0262": {"name": "法華經", "full_name": "妙法蓮華經", "length": "長", "difficulty": "中"},
            "T0945": {"name": "楞嚴經", "full_name": "大佛頂首楞嚴經", "length": "長", "difficulty": "較高"},
            "T0293": {"name": "普賢行願品", "full_name": "普賢菩薩行願品", "length": "中", "difficulty": "中"},
            "T0412": {"name": "地藏經", "full_name": "地藏菩薩本願經", "length": "中", "difficulty": "入門"},
            "T0449": {"name": "藥師經", "full_name": "藥師琉璃光如來本願功德經", "length": "短", "difficulty": "入門"},
            "T2008": {"name": "六祖壇經", "full_name": "六祖大師法寶壇經", "length": "中", "difficulty": "中"},
            "T1911": {"name": "摩訶止觀", "full_name": "摩訶止觀", "length": "長", "difficulty": "高"},
            "T1585": {"name": "成唯識論", "full_name": "成唯識論", "length": "長", "difficulty": "高"},
            "T1579": {"name": "瑜伽師地論", "full_name": "瑜伽師地論", "length": "很長", "difficulty": "高"},
            "T1586": {"name": "唯識三十頌", "full_name": "唯識三十論頌", "length": "短", "difficulty": "中高"},
            "T1564": {"name": "中論", "full_name": "中論", "length": "中", "difficulty": "高"},
            "T2005": {"name": "無門關", "full_name": "無門關", "length": "短", "difficulty": "中"},
            "X1001": {"name": "碧巌錄", "full_name": "碧巌錄", "length": "中", "difficulty": "高"},
            "T1956": {"name": "天台小止觀", "full_name": "修習止觀坐禪法要", "length": "短", "difficulty": "中"},
            "T1484": {"name": "梵網經", "full_name": "梵網經", "length": "中", "difficulty": "中"},
            "T1428": {"name": "四分律", "full_name": "四分律", "length": "長", "difficulty": "中高"},
            "T1568": {"name": "十二門論", "full_name": "十二門論", "length": "中", "difficulty": "高"},
            "T0220": {"name": "大般若經", "full_name": "大般若波羅蜜多經", "length": "非常長", "difficulty": "高"},
        }
        
        logger.info("經典推薦服務初始化成功")
    
    async def recommend_related_sutras(self, query: str, mentioned_sutra_id: str = None) -> List[Dict]:
        """
        推薦與用戶查詢相關的經典

        Args:
            query: 用戶問題
            mentioned_sutra_id: 已提及的經典ID (可選)

        Returns:
            List[Dict]: 推薦的經典列表
        """
        try:
            # 確保初學者優先看到金剛經或普賢行願品
            user_level = self._determine_user_level(query)
            recommendations = []
            
            # 如果已有提到某個經典，先推薦相同類別的經典
            if mentioned_sutra_id:
                category = self._get_sutra_category(mentioned_sutra_id)
                if category:
                    for sutra_id in self.sutra_categories.get(category, []):
                        # 跳過已提及的經典
                        if sutra_id == mentioned_sutra_id:
                            continue
                        
                        # 檢查經典是否適合用戶級別
                        if not self._is_suitable_for_level(sutra_id, user_level):
                            continue
                            
                        sutra_info = self._get_sutra_info(sutra_id)
                        if sutra_info:
                            recommendations.append(sutra_info)
                    
                    # 隨機選擇最多2個相同類別的推薦
                    if recommendations:
                        random.shuffle(recommendations)
                        recommendations = recommendations[:2]

            # 基於用戶級別添加基礎推薦
            base_recommendations = self._get_base_recommendations(user_level)
            if base_recommendations:
                # 確保不重複推薦
                for rec in base_recommendations:
                    if rec["id"] not in [r["id"] for r in recommendations] and rec["id"] != mentioned_sutra_id:
                        recommendations.append(rec)
            
            # 如果推薦數量不足，基於查詢添加更多推薦
            if len(recommendations) < 3:
                query_recommendations = await self._get_query_based_recommendations(query, user_level)
                for rec in query_recommendations:
                    if rec["id"] not in [r["id"] for r in recommendations] and rec["id"] != mentioned_sutra_id:
                        recommendations.append(rec)
                        if len(recommendations) >= 3:
                            break
            
            # 格式化推薦結果
            formatted_recommendations = []
            for rec in recommendations[:3]:  # 最多返回3個推薦
                formatted_rec = self._format_recommendation(rec)
                if formatted_rec:
                    formatted_recommendations.append(formatted_rec)
            
            return formatted_recommendations
            
        except Exception as e:
            logging.error(f"生成經典推薦時出錯: {e}", exc_info=True)
            # 返回默認推薦
            return self._get_default_recommendations()

    def _determine_user_level(self, query: str) -> str:
        """根據查詢確定用戶修行水平"""
        # 初學者相關關鍵詞
        beginner_keywords = ["入門", "初學", "基礎", "開始", "如何修行", "怎麼開始", 
                            "初步", "新手", "剛接觸", "入道", "皈依", "初發心"]
        
        # 中級相關關鍵詞
        intermediate_keywords = ["禪修", "專注", "戒律", "六度", "發心", "菩提心", 
                                "空性", "止觀", "正念", "持戒", "出離心"]
        
        # 進階相關關鍵詞
        advanced_keywords = ["見性", "解脫", "涅槃", "中觀", "圓融", "法界", "實相", 
                            "如來藏", "八識", "唯識", "四空", "密法", "本尊"]
        
        # 默認為初學者級別
        level = "beginner"
        
        # 檢查查詢中的關鍵詞
        query_lower = query.lower()
        
        # 如果包含進階關鍵詞，判定為進階
        for keyword in advanced_keywords:
            if keyword in query_lower:
                level = "advanced"
                break
        
        # 如果沒有判定為進階，檢查是否為中級
        if level == "beginner":
            for keyword in intermediate_keywords:
                if keyword in query_lower:
                    level = "intermediate"
                    break
        
        return level

    def _is_suitable_for_level(self, sutra_id: str, user_level: str) -> bool:
        """判斷經典是否適合用戶級別"""
        # 特定經典的難度分級
        beginner_sutras = ["T0235", "T0251", "T0293", "T0366", "T0412"]  # 金剛經、心經、普賢行願品、阿彌陀經、地藏經
        intermediate_sutras = ["T0262", "T0945", "T0449", "T2008"]  # 法華經、楞嚴經、藥師經、六祖壇經
        advanced_sutras = ["T1585", "T1586", "T1579", "T1911", "T1564", "T0220"]  # 唯識、中觀、摩訶止觀等
        
        if user_level == "beginner":
            return sutra_id in beginner_sutras
        elif user_level == "intermediate":
            return sutra_id in beginner_sutras or sutra_id in intermediate_sutras
        else:  # advanced
            return True  # 進階用戶可以接受任何級別的經典
    
    def _get_base_recommendations(self, user_level: str) -> List[Dict]:
        """根據用戶級別獲取基礎推薦"""
        recommendations = []
        
        if user_level == "beginner":
            # 初學者優先推薦金剛經或普賢行願品
            key_sutras = ["T0235", "T0293"]  # 金剛經、普賢行願品
            for sutra_id in key_sutras:
                sutra_info = self._get_sutra_info(sutra_id)
                if sutra_info:
                    recommendations.append(sutra_info)
        
        elif user_level == "intermediate":
            # 中級推薦楞嚴經、地藏經等
            key_sutras = ["T0945", "T0412"]  # 楞嚴經、地藏經
            for sutra_id in key_sutras:
                sutra_info = self._get_sutra_info(sutra_id)
                if sutra_info:
                    recommendations.append(sutra_info)
        
        else:  # advanced
            # 進階推薦法華經、摩訶止觀等
            key_sutras = ["T0262", "T1911"]  # 法華經、摩訶止觀
            for sutra_id in key_sutras:
                sutra_info = self._get_sutra_info(sutra_id)
                if sutra_info:
                    recommendations.append(sutra_info)
        
        # 隨機選擇以增加多樣性
        if recommendations:
            random.shuffle(recommendations)
            return recommendations[:2]  # 最多返回2個基礎推薦
        
        return []
    
    def _get_sutra_category(self, sutra_id: str) -> Optional[str]:
        """
        獲取經典所屬分類
        
        Args:
            sutra_id: 經典ID
            
        Returns:
            Optional[str]: 分類名稱
        """
        for category, sutras in self.sutra_categories.items():
            if sutra_id in sutras:
                return category
        return None
    
    def _format_recommendation(self, sutra_id: str) -> Optional[Dict[str, Any]]:
        """
        格式化經典推薦信息
        
        Args:
            sutra_id: 經典ID
            
        Returns:
            Optional[Dict]: 格式化的推薦信息
        """
        info = self.sutra_info.get(sutra_id)
        if not info:
            return None
            
        return {
            "id": sutra_id,
            "name": info.get("name", "未知經典"),
            "full_name": info.get("full_name", ""),
            "description": f"{info.get('name', '')}（{info.get('length', '')}篇，{info.get('difficulty', '')}難度）",
            "cbeta_url": f"https://cbetaonline.dila.edu.tw/zh/{sutra_id}"
        }

    async def _get_query_based_recommendations(self, query: str, user_level: str) -> List[Dict]:
        """根據查詢内容獲取推薦經典"""
        try:
            # 調用經文檢索服務查詢相關經典
            query_results = await self.sutra_retriever.query_sutra(query, top_k=5, use_rerank=True)
            
            recommendations = []
            for result in query_results:
                sutra_id = result.get("sutra_id")
                if not sutra_id:
                    continue
                    
                # 檢查經典是否適合用戶級別
                if not self._is_suitable_for_level(sutra_id, user_level):
                    continue
                    
                # 獲取經典信息
                sutra_info = self._get_sutra_info(sutra_id)
                if sutra_info and sutra_id not in [r.get("id") for r in recommendations]:
                    recommendations.append(sutra_info)
            
            return recommendations
            
        except Exception as e:
            logging.error(f"基於查詢獲取推薦時出錯: {e}", exc_info=True)
            return []
    
    def _get_sutra_info(self, sutra_id: str) -> Optional[Dict]:
        """獲取經典的詳細信息"""
        info = self.sutra_info.get(sutra_id)
        if not info:
            return None
            
        return {
            "id": sutra_id,
            "name": info.get("name", "未知經典"),
            "full_name": info.get("full_name", ""),
            "description": f"{info.get('name', '')}（{info.get('length', '')}篇，{info.get('difficulty', '')}難度）",
            "cbeta_url": f"https://cbetaonline.dila.edu.tw/zh/{sutra_id}"
        }
    
    def _get_default_recommendations(self) -> List[Dict]:
        """獲取默認推薦，用於出錯時的後備方案"""
        default_recommendations = []
        default_sutras = ["T0235", "T0251", "T0293"]  # 金剛經、心經、普賢行願品
        
        for sutra_id in default_sutras:
            formatted_rec = self._format_recommendation(sutra_id)
            if formatted_rec:
                default_recommendations.append(formatted_rec)
        
        return default_recommendations

# 創建單例實例
sutra_recommender = SutraRecommender() 
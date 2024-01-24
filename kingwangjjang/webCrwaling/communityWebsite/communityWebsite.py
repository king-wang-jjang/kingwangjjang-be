from abc import abstractmethod


class AbstractCommunityWebsite():
    dayBestUrl = ''
    realtimeBestUrl = ''
    
    @abstractmethod
    def GetDayBest(self):
        return {}        

    @abstractmethod
    def GetRealTimeBest(self):
        return {} 
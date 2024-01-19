from abc import abstractmethod


class AbstractCommunityWebsite():
    dayBestUrl = ''
    realtimeBestUrl = ''
    
    @abstractmethod
    def getDayBest():
        return {}        

    @abstractmethod
    def getRealTimeBest():
        return {} 
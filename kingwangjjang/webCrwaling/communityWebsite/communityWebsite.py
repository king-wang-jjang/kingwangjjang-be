from abc import abstractmethod


class AbstractCommunityWebsite():
    dayBestUrl = ''
    realtimeBestUrl = ''
    
    @abstractmethod
    def get_daily_best(self):
        return {}        

    @abstractmethod
    def get_real_time_best(self):
        return {} 
    
    @abstractmethod
    def get_board_contents(self, board_id):
        return {} 
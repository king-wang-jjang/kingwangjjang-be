from fastapi import FastAPI

# Decorator
def constant(func):
    def func_set(self, value):
        raise TypeError

    def func_get(self):
        return func()
    return property(func_get, func_set)

class ApiPaths(object):
    @constant
    def ROOT():
        return "/"

    @constant
    def SEPARATE():
        return "/"
    
    @constant
    def V1(cls):
        return cls.ROOT + "V1"
    
    # -------------------로그인 Auth----------------------
    
    @constant
    def AUTH(cls):
        return cls.V1 + "AUTH"
    
    #Auth
    @constant
    def LOGIN_WITH_MS(cls):
        return cls.AUTH + "login"
    
    #로그인
    @constant
    def AUTH_CALLBACK(cls):
        return cls.AUTH + "auth" + cls.ROOT + "callback"
    
    #로그아웃
    @constant
    def LOGOUT(cls):
        return cls.AUTH + "logout"
    
    #세션 체크
    @constant
    def CHECK_SESSION(cls):
        return cls.AUTH + "validate"
    
    
    # -------------------전체 고객 검색 User----------------------  

    @constant
    def USER(cls):
        return cls.V1 + "USER"
   
    # 고객 READ
    @constant
    def READ_USER(cls):
        return cls.USER + cls.SEPARATE + "readUser"
   
    # 고객 CREATE
    @constant
    def CREATE_USER(cls):
        return cls.USER + cls.SEPARATE + "createUser"
   
    # 고객 UPDATE
    @constant
    def UPDATE_USER(cls):
        return cls.USER + cls.SEPARATE + "updateUser"
   
    # 고객 DELETE
    @constant
    def DELETE_USER(cls):
        return cls.USER + cls.SEPARATE + "deleteUser"
        
    
    # -------------------작업 요청 상태 확인 및 전체 작업 현황 Request----------------------    
        
    @constant
    def REQUEST(cls):
        return cls.V1 + "REQUEST"
   
    # 작업 요청 READ
    @constant
    def READ_REQUEST(cls):
        return cls.REQUEST + cls.SEPARATE + "readRequest"
   
    # 작업 요청 CREATE
    @constant
    def CREATE_REQUEST(cls):
        return cls.REQUEST + cls.SEPARATE + "createRequest"
   
    # 작업 요청 UPDATE
    @constant
    def UPDATE_REQUEST(cls):
        return cls.REQUEST + cls.SEPARATE + "updateRequest"
   
    # 작업 요청 DELETE
    @constant
    def DELETE_REQUEST(cls):
        return cls.REQUEST + cls.SEPARATE + "deleteRequest"
   
       
    # -------------------계약 사항 확인 Contract----------------------    
    
    @constant
    def CONTRACT(cls):
        return cls.V1 + "CONTRACT"
   
    # 계약 사항 READ
    @constant
    def READ_CONTRACT(cls):
        return cls.CONTRACT + cls.SEPARATE + "readContract"
   
    # 계약 사항 CREATE
    @constant
    def CREATE_CONTRACT(cls):
        return cls.CONTRACT + cls.SEPARATE + "createContract"
   
    # 계약 사항 UPDATE
    @constant
    def UPDATE_CONTRACT(cls):
        return cls.CONTRACT + cls.SEPARATE + "updateContract"
   
    # 계약 사항 DELETE
    @constant
    def DELETE_CONTRACT(cls):
        return cls.CONTRACT + cls.SEPARATE + "deleteContract"
    
    # -------------------과금 세금 계산서 Tax----------------------    
     
    @constant
    def TAX(cls):
        return cls.V1 + "TAX"
   
    # 세금계산서 READ
    @constant
    def READ_TAX(cls):
        return cls.TAX + cls.SEPARATE + "readTax"
   
    # 세금계산서 CREATE
    @constant
    def CREATE_TAX(cls):
        return cls.TAX + cls.SEPARATE + "createTax"
   
    # 세금계산서 UPDATE
    @constant
    def UPDATE_TAX(cls):
        return cls.TAX + cls.SEPARATE + "updateTax"
   
    # 세금계산서 DELETE
    @constant
    def DELETE_TAX(cls):
        return cls.TAX + cls.SEPARATE + "deleteTax"    
    
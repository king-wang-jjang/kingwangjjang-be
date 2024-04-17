from ftplib import FTP
import os
import logging

logger = logging.getLogger("")

class FTPClient(object):
    _instance = None  
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:  
            cls._instance = super().__new__(cls)
            return cls._instance
        else:
            return cls._instance

    def __init__(self, server_address, username, password):
        """
        FTP client 설정

        Args:
            server_address: ip address 
            username: username
            password: password
        """
        if not hasattr(self, 'initialized'):  
            self.root = "/home"
            self.server_address = server_address
            self.username = username
            self.password = password
            self.ftp = FTP()
            try:
                self.ftp.connect(self.server_address)
                self.ftp.login(self.username, self.password)
                logger.info("Successfully FTP connected")
            except Exception as e:
                logger.info(f'FTP Error: {e}')
                raise  # 예외 발생
            else:
                self.initialized = True

    def list_files(self, directory):
        try:
            files = []
            self.ftp.cwd(directory)
            self.ftp.dir(files.append)
            return files
        except Exception as e:
            logger.info(f'FTP Error: {e}')
            return []
        
    def ftp_upload_file(self, local_file_path):
        file_name = os.path.basename(local_file_path)  
        full_remote_path = f'{self.ftp.pwd()}/{file_name}'
        logger.info('full_remote_path', full_remote_path)
        try:
            with open(local_file_path, 'rb') as file:
                self.ftp.storbinary(f'STOR {full_remote_path}', file)
            logger.info(f'File uploaded successfully to {full_remote_path}')

        except Exception as e:
            logger.info(f'FTP Error: {e}')

    def ftp_download_file(self, remote_file_path, local_file_path):
        try:
            with open(local_file_path, 'wb') as file:
                self.ftp.retrbinary(f'RETR {remote_file_path[1:]}', file.write)

            logger.info(f'File downloaded successfully to {local_file_path}')

        except Exception as e:
            logger.info(f'FTP Error: {e}')

    def ftp_upload_folder(self, local_directory, remote_directory):
            """
            폴더 안에 모든 파일을 업로드

            Args:
                local_directory: Path to the local directory.
                remote_directory: 단일 이여야함 중첩이면 안됨
            """
            try:
                self.ftp.mkd(remote_directory)
                # self.create_directory(remote_directory)
                self.ftp.cwd(self.root + '/' + remote_directory)
                logger.info(f"FTP Server Directory created: {remote_directory}")
            except Exception as e:
                if "550" in str(e):
                    logger.info('FTP Server directory already exists')
                    self.ftp.cwd(self.root + '/'  + remote_directory)
                    pass
                else:
                    logger.info(f"error occurred: {e}")
            for filename in os.listdir(local_directory):
                local_path = os.path.join(local_directory, filename).replace('\\', '/')  # windows에서 \\로 표시되는데 linux에서는 어떨지 봐야함
                remote_path = os.path.join(remote_directory, filename).replace('\\', '/')
                if os.path.isfile(local_path):
                    self.ftp_upload_file(local_path)
                else:
                    self.ftp_upload_folder(local_path, remote_path)  
            self.ftp.cwd(self.root)
            logger.info(f'FTP Server Folder uploaded successfully to {remote_directory}')

    def create_directory(self, directory):
        """
        Creates a directory on the FTP server.
        CWD
        Args:
            directory: Path of the directory to be created.
        """
        folders = directory.split("/")
        for folder in folders:
            try:
                self.ftp.mkd(folder)
                self.ftp.cwd(folder)
            except Exception as e:
                if "550" in str(e):
                    pass
                else:
                    raise
    
    
    def create_today_directory(self, yyyymmdd):
        """
        CommunityWebsite인 super class만 사용
        최소 수행

        Args:
            yyyymmdd: directory name
        """
        try:
            self.ftp.cwd(self.root)
            self.ftp.cwd(yyyymmdd)
            self.root = self.root + "/" + yyyymmdd
        except Exception as e:
            try:
                self.ftp.mkd(yyyymmdd)
                self.ftp.cwd(yyyymmdd)
                self.root = self.root + "/" + yyyymmdd
                logger.info(f"Directory created: {yyyymmdd}")
            except Exception as e:
                raise ValueError(f"Error creating directory: {e}")
            else:
                return True
        else:
            return True
from ftplib import FTP
import ftplib
import os

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
                print("Successfully FTP connected")
            except Exception as e:
                print(f'FTP Error: {e}')
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
            print(f'FTP Error: {e}')
            return []
        
    def ftp_upload_file(self, local_file_path, remote_file_path):
        try:
            with open(local_file_path, 'rb') as file:
                self.ftp.storbinary(f'STOR {remote_file_path}', file)
            print(f'File uploaded successfully to {remote_file_path}')

        except Exception as e:
            print(f'FTP Error: {e}')

    def ftp_download_file(self, remote_file_path, local_file_path):
        try:
            with open(local_file_path, 'wb') as file:
                self.ftp.retrbinary(f'RETR {remote_file_path}', file.write)

            print(f'File downloaded successfully to {local_file_path}')

        except Exception as e:
            print(f'FTP Error: {e}')

    def ftp_upload_folder(self, local_directory, remote_directory):
            """
            폴더 안에 모든 파일을 업로드

            Args:
                local_directory: Path to the local directory.
                remote_directory: Path to the remote directory on the FTP server.
            """
            try:
                self.ftp.mkd(remote_directory)
                print(f"Directory created: {remote_directory}")
            except ftplib.error_perm as e: 
                print(f"Directory already exists or error occurred: {e}")
            
            for filename in os.listdir(local_directory):
                local_path = os.path.join(local_directory, filename).replace('\\', '/')  # windows에서 \\로 표시되는데 linux에서는 어떨지 봐야함
                remote_path = os.path.join(remote_directory, filename).replace('\\', '/')
                if os.path.isfile(local_path):
                    self.ftp_upload_file(local_path, remote_path)
                else:
                    self.ftp_upload_folder(local_path, remote_path)  

            print(f'Folder uploaded successfully to {remote_directory}')

    def create_directory(self, directory):
        """
        Creates a directory on the FTP server.

        Args:
            directory: Path of the directory to be created.
        """
        try:
            self.ftp.mkd(directory)
            print(f"Directory created: {directory}")
        except ftplib.error_perm as e:
            parent_dir = os.path.dirname(directory)
            if parent_dir:
                self.create_directory(parent_dir)
                self.create_directory(directory)
            else:
                print(f"Error creating directory: {e}")
        except Exception as e:
            print(f"Error creating directory: {e}")
    
    
    def create_today_directory(self, yyyymmdd):
        """
        CommunityWebsite인 super class만 사용

        Args:
            yyyymmdd: directory name
        """
        try:
            self.ftp.cwd(self.root)
            self.ftp.cwd(yyyymmdd)
            # print(f"Directory already exists: {yyyymmdd}")
        except Exception as e:
            try:
                self.ftp.mkd(yyyymmdd)
                self.ftp.cwd(yyyymmdd)
                print(f"Directory created: {yyyymmdd}")
            except Exception as e:
                raise ValueError(f"Error creating directory: {e}")
            else:
                return True
        else:
            return True
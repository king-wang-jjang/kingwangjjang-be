from ftplib import FTP

class FTPClient(object):
    def __init__(self, server_address, username, password):
        self.server_address = server_address
        self.username = username
        self.password = password

    def ftp_upload_file(self, local_file_path, remote_file_path):
        try:
            with FTP() as ftp:
                ftp.connect(self.server_address)
                ftp.login(self.username, self.password)

                with open(local_file_path, 'rb') as file:
                    ftp.storbinary(f'STOR {remote_file_path}', file)

                print(f'File uploaded successfully to {remote_file_path}')

        except Exception as e:
            print(f'Error: {e}')

    def ftp_download_file(self, remote_file_path, local_file_path):
        try:
            with FTP() as ftp:
                ftp.connect(self.server_address)
                ftp.login(self.username, self.password)

                with open(local_file_path, 'wb') as file:
                    ftp.retrbinary(f'RETR {remote_file_path}', file.write)

                print(f'File downloaded successfully to {local_file_path}')

        except Exception as e:
            print(f'Error: {e}')
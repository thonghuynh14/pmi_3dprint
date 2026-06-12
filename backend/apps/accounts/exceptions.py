"""Domain exceptions cho accounts.

DRF tự render thành response 4xx (qua exception_handler default).
"""

from rest_framework import status
from rest_framework.exceptions import APIException


class InvalidCredentialsError(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Tên đăng nhập hoặc mật khẩu không đúng."
    default_code = "invalid_credentials"


class UserInactiveError(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Tài khoản đã bị vô hiệu hoá."
    default_code = "user_inactive"

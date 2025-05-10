import re, random, secrets
import graphene
from django.contrib.auth import get_user_model, authenticate
from django.core.mail import EmailMultiAlternatives
from django.contrib.auth.password_validation import validate_password, ValidationError as PasswordValidationError
from graphql_jwt.decorators import login_required
from graphene_django import DjangoObjectType
from rest_framework_simplejwt.tokens import RefreshToken
import graphql_jwt
from graphql_jwt.shortcuts import get_token

from back.common.models import EmailVerification

User = get_user_model()
EMAIL_REGEX = r'^[\w\.-]+@[\w\.-]+\.\w+$'


class UserType(DjangoObjectType):
  class Meta:
    model = User


class EmailVerificationType(DjangoObjectType):
  class Meta:
    model = EmailVerification


class Register(graphene.Mutation):
  class Arguments:
    email = graphene.String(required=True)
    name = graphene.String(required=True)
    password = graphene.String(required=True)
    token = graphene.String(required=True)

  message = graphene.String()

  def mutate(self, info, email, name, password, token):
    if not re.match(EMAIL_REGEX, email):
      raise Exception('이메일 형식이 올바르지 않습니다.')

    if User.objects.filter(email=email).exists():
      raise Exception('이미 해당 이메일로 가입된 계정이 존재합니다.')

    try:
      record = EmailVerification.objects.filter(email=email, purpose='register').latest('created_at')
    except EmailVerification.DoesNotExist:
      raise Exception('이메일 인증 요청 기록이 없습니다.')

    if record.token != token:
      raise Exception('유효하지 않은 인증 토큰입니다.')

    if record.purpose != 'register':
      raise Exception('유효하지 않은 인증 요청입니다.')

    try:
      validate_password(password)
    except PasswordValidationError as e:
      raise Exception(f'비밀번호 오류: {" ".join(e.messages)}')

    user = User.objects.create_user(email=email, name=name, password=password)
    record.delete()
    return Register(message='회원가입 성공!')


class Login(graphene.Mutation):
  class Arguments:
    email = graphene.String(required=True)
    password = graphene.String(required=True)

  message = graphene.String()
  access = graphene.String()
  refresh = graphene.String()
  email = graphene.String()
  name = graphene.String()

  def mutate(self, info, email, password):
    if not re.match(EMAIL_REGEX, email):
      raise Exception('이메일 형식이 올바르지 않습니다.')

    user = authenticate(email=email, password=password)
    if not user:
      raise Exception('이메일 또는 비밀번호가 틀렸습니다.')

    token = get_token(user)

    return Login(
      message='로그인 성공',
      access=token,
      refresh="",
      email=user.email,
      name=user.name
    )


class SendVerificationCode(graphene.Mutation):
  class Arguments:
    email = graphene.String(required=True)

  message = graphene.String()

  def mutate(self, info, email):
    if not re.match(EMAIL_REGEX, email):
      raise Exception('이메일 형식이 올바르지 않습니다.')

    if User.objects.filter(email=email).exists():
      raise Exception('이미 해당 이메일로 가입된 계정이 존재합니다.')

    code = str(random.randint(100000, 999999))
    EmailVerification.objects.filter(email=email, purpose='register').delete()
    EmailVerification.objects.create(email=email, code=code, purpose='register')

    subject = '[KOREAT] 회원가입 인증번호 안내'
    body = f'''
    <html><body style="font-family: Arial;">
      <h2 style="color: #4CAF50;">KOREAT 회원가입 인증번호</h2>
      <p>아래 인증번호를 5분 이내에 입력해주세요.</p>
      <div style="font-size: 30px; font-weight: bold; margin: 20px 0;">{code}</div>
    </body></html>'''

    try:
      message = EmailMultiAlternatives(subject, '회원가입 인증번호입니다.', to=[email])
      message.attach_alternative(body, "text/html")
      message.send()
      return SendVerificationCode(message='인증번호가 이메일로 전송되었습니다.')
    except Exception as e:
      raise Exception(f'이메일 전송 실패: {str(e)}')


class VerifyEmailCode(graphene.Mutation):
  class Arguments:
    email = graphene.String(required=True)
    code = graphene.String(required=True)

  message = graphene.String()
  token = graphene.String()

  def mutate(self, info, email, code):
    try:
      record = EmailVerification.objects.filter(email=email, purpose='register').latest('created_at')
    except EmailVerification.DoesNotExist:
      raise Exception('인증 요청 기록이 없습니다.')

    if record.is_expired():
      raise Exception('인증번호가 만료되었습니다.')

    if record.code != code:
      raise Exception('인증번호가 일치하지 않습니다.')

    one_time_token = secrets.token_urlsafe(32)
    record.token = one_time_token
    record.save()

    return VerifyEmailCode(message='이메일 인증 성공', token=one_time_token)


class SendResetCode(graphene.Mutation):
  class Arguments:
    email = graphene.String(required=True)

  message = graphene.String()

  def mutate(self, info, email):
    if not re.match(EMAIL_REGEX, email):
      raise Exception('이메일 형식이 올바르지 않습니다.')

    if not User.objects.filter(email=email).exists():
      raise Exception('해당 이메일로 가입된 사용자가 없습니다.')

    code = str(random.randint(100000, 999999))
    EmailVerification.objects.filter(email=email, purpose='reset').delete()
    EmailVerification.objects.create(email=email, code=code, purpose='reset')

    subject = '[KOREAT] 비밀번호 재설정 인증번호 안내'
    body = f'''
    <html><body style="font-family: Arial;">
      <h2 style="color: #FF5722;">KOREAT 비밀번호 재설정 인증번호</h2>
      <p>아래 인증번호를 5분 이내에 입력해주세요.</p>
      <div style="font-size: 30px; font-weight: bold; margin: 20px 0;">{code}</div>
    </body></html>'''

    try:
      message = EmailMultiAlternatives(subject, '비밀번호 재설정 인증번호입니다.', to=[email])
      message.attach_alternative(body, "text/html")
      message.send()
      return SendResetCode(message='인증번호가 이메일로 전송되었습니다.')
    except Exception as e:
      raise Exception(f'이메일 전송 실패: {str(e)}')


class VerifyResetCode(graphene.Mutation):
  class Arguments:
    email = graphene.String(required=True)
    code = graphene.String(required=True)

  message = graphene.String()
  token = graphene.String()

  def mutate(self, info, email, code):
    try:
      record = EmailVerification.objects.filter(email=email, purpose='reset').latest('created_at')
    except EmailVerification.DoesNotExist:
      raise Exception('비밀번호 재설정 요청 기록이 없습니다.')

    if record.is_expired():
      raise Exception('인증번호가 만료되었습니다.')

    if record.code != code:
      raise Exception('인증번호가 일치하지 않습니다.')

    one_time_token = secrets.token_urlsafe(32)
    record.token = one_time_token
    record.save()

    return VerifyResetCode(message='인증 성공', token=one_time_token)


class ResetPassword(graphene.Mutation):
  class Arguments:
    email = graphene.String(required=True)
    token = graphene.String(required=True)
    new_password = graphene.String(required=True)

  message = graphene.String()

  def mutate(self, info, email, token, new_password):
    try:
      record = EmailVerification.objects.filter(email=email, purpose='reset').latest('created_at')
    except EmailVerification.DoesNotExist:
      raise Exception('비밀번호 재설정 요청 기록이 없습니다.')

    if record.token != token:
      raise Exception('유효하지 않은 토큰입니다.')

    try:
      validate_password(new_password)
    except PasswordValidationError as e:
      raise Exception(f'비밀번호 오류: {" ".join(e.messages)}')

    try:
      user = User.objects.get(email=email)
      user.set_password(new_password)
      user.save()
      record.delete()
      return ResetPassword(message='비밀번호가 성공적으로 변경되었습니다.')
    except User.DoesNotExist:
      raise Exception('사용자를 찾을 수 없습니다.')

class UpdateUsername(graphene.Mutation):
  class Arguments:
    name = graphene.String(required=True)

  message = graphene.String()
  name = graphene.String()

  @login_required
  def mutate(self, info, name):
    user = info.context.user
    user.name = name
    user.save()
    return UpdateUsername(message='이름이 성공적으로 변경되었습니다.', name=name)


class DeleteAccount(graphene.Mutation):
  message = graphene.String()

  @login_required
  def mutate(self, info):
    user = info.context.user
    user.delete()
    return DeleteAccount(message='회원 탈퇴가 완료되었습니다.')


class Mutation(graphene.ObjectType):
  register = Register.Field()
  login = Login.Field()
  send_verification_code = SendVerificationCode.Field()
  verify_email_code = VerifyEmailCode.Field()
  send_reset_code = SendResetCode.Field()
  verify_reset_code = VerifyResetCode.Field()
  reset_password = ResetPassword.Field()
  update_username = UpdateUsername.Field()
  delete_account = DeleteAccount.Field()
  token_auth = graphql_jwt.ObtainJSONWebToken.Field()
  verify_token = graphql_jwt.Verify.Field()
  refresh_token = graphql_jwt.Refresh.Field()

class Query(graphene.ObjectType):
  me = graphene.Field(UserType)

  
  def resolve_me(self, info):
    return info.context.user

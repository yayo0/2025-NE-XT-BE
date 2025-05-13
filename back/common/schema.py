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
      raise Exception('Invalid email format.')

    if User.objects.filter(email=email).exists():
      raise Exception('An account with this email already exists.')

    try:
      record = EmailVerification.objects.filter(email=email, purpose='register').latest('created_at')
    except EmailVerification.DoesNotExist:
      raise Exception('No email verification request found.')

    if record.token != token:
      raise Exception('Invalid verification token.')

    if record.purpose != 'register':
      raise Exception('Invalid verification request.')

    try:
      validate_password(password)
    except PasswordValidationError as e:
      raise Exception(f'Password error: {" ".join(e.messages)}')

    user = User.objects.create_user(email=email, name=name, password=password)
    record.delete()
    return Register(message='Registration successful!')


class Login(graphene.Mutation):
  class Arguments:
    email = graphene.String(required=True)
    password = graphene.String(required=True)

  message = graphene.String()
  access = graphene.String()
  refresh = graphene.String()
  email = graphene.String()
  name = graphene.String()
  is_staff = graphene.Boolean()

  def mutate(self, info, email, password):
    if not re.match(EMAIL_REGEX, email):
      raise Exception('Invalid email format.')

    user = authenticate(email=email, password=password)
    if not user:
      raise Exception('Incorrect email or password.')

    token = get_token(user)

    return Login(
      message='Login successful',
      access=token,
      refresh="",
      email=user.email,
      name=user.name,
      is_staff=user.is_staff
    )


class SendVerificationCode(graphene.Mutation):
  class Arguments:
    email = graphene.String(required=True)

  message = graphene.String()

  def mutate(self, info, email):
    if not re.match(EMAIL_REGEX, email):
      raise Exception('Invalid email format.')

    if User.objects.filter(email=email).exists():
      raise Exception('An account with this email already exists.')

    code = str(random.randint(100000, 999999))
    EmailVerification.objects.filter(email=email, purpose='register').delete()
    EmailVerification.objects.create(email=email, code=code, purpose='register')

    subject = '[KOREAT] Registration Verification Code'
    body = f'''
<html>
  <body style="margin:0; padding:0; font-family:Arial,sans-serif; background-color:#f3f4f6">
    <table width="100%" cellpadding="0" cellspacing="0" bgcolor="#f3f4f6">
      <tr>
        <td align="center" style="padding:60px 0">
          <table width="600" cellpadding="0" cellspacing="0" bgcolor="#ffffff"
            style="border:1px solid #e2e8f0; border-radius:8px; overflow:hidden">
            <tr>
              <td align="center" bgcolor="#2f3437" style="padding:20px">
                <h1 style="margin:0; color:#ffffff; font-size:26px">KOREAT</h1>
              </td>
            </tr>
            <tr>
              <td align="center" style="padding:40px">
                <p style="margin:0 0 10px 0; color:#333333; font-size:18px">Verification Code</p>
                <p style="margin:0; color:#000000; font-size:36px; font-weight:bold">
                  {code}
                </p>
                <p style="margin:10px 0 0 0; color:#777777; font-size:14px">
                  This code will expire in 5 minutes
                </p>
              </td>
            </tr>
            <tr>
              <td style="padding:20px; border-top:1px solid #e2e8f0">
                <p style="margin:0; color:#555555; font-size:12px">
                  If you did not request this email, please ignore it.  
                  For assistance, contact us at  
                  <a href="mailto:hensin12@gmail.com" style="color:#2f3437; text-decoration:none">
                    hensin12@gmail.com
                  </a>
                </p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
'''

    try:
      message = EmailMultiAlternatives(subject, 'Registration verification code.', to=[email])
      message.attach_alternative(body, "text/html")
      message.send()
      return SendVerificationCode(message='Verification code has been sent to your email.')
    except Exception as e:
      raise Exception(f'Failed to send email: {str(e)}')


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
      raise Exception('No verification request record found.')

    if record.is_expired():
      raise Exception('Verification code has expired.')

    if record.code != code:
      raise Exception('Incorrect verification code.')

    one_time_token = secrets.token_urlsafe(32)
    record.token = one_time_token
    record.save()

    return VerifyEmailCode(message='Email verification successful', token=one_time_token)


class SendResetCode(graphene.Mutation):
  class Arguments:
    email = graphene.String(required=True)

  message = graphene.String()

  def mutate(self, info, email):
    if not re.match(EMAIL_REGEX, email):
      raise Exception('Invalid email format.')

    if not User.objects.filter(email=email).exists():
      raise Exception('No user registered with this email.')

    code = str(random.randint(100000, 999999))
    EmailVerification.objects.filter(email=email, purpose='reset').delete()
    EmailVerification.objects.create(email=email, code=code, purpose='reset')

    subject = '[KOREAT] Password Reset Verification Code'
    body = f'''
<html>
  <body style="margin:0; padding:0; font-family:Arial,sans-serif; background-color:#f3f4f6">
    <table width="100%" cellpadding="0" cellspacing="0" bgcolor="#f3f4f6">
      <tr>
        <td align="center" style="padding:60px 0">
          <table width="600" cellpadding="0" cellspacing="0" bgcolor="#ffffff"
            style="border:1px solid #e2e8f0; border-radius:8px; overflow:hidden">
            <tr>
              <td align="center" bgcolor="#2f3437" style="padding:20px">
                <h1 style="margin:0; color:#ffffff; font-size:26px">KOREAT</h1>
              </td>
            </tr>
            <tr>
              <td align="center" style="padding:40px">
                <p style="margin:0 0 10px 0; color:#333333; font-size:18px">Verification Code</p>
                <p style="margin:0; color:#000000; font-size:36px; font-weight:bold">
                  {code}
                </p>
                <p style="margin:10px 0 0 0; color:#777777; font-size:14px">
                  This code will expire in 5 minutes
                </p>
              </td>
            </tr>
            <tr>
              <td style="padding:20px; border-top:1px solid #e2e8f0">
                <p style="margin:0; color:#555555; font-size:12px">
                  If you did not request this email, please ignore it.  
                  For assistance, contact us at  
                  <a href="mailto:hensin12@gmail.com" style="color:#2f3437; text-decoration:none">
                    hensin12@gmail.com
                  </a>
                </p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
'''

    try:
      message = EmailMultiAlternatives(subject, 'Password reset verification code.', to=[email])
      message.attach_alternative(body, "text/html")
      message.send()
      return SendResetCode(message='Verification code has been sent to your email.')
    except Exception as e:
      raise Exception(f'Failed to send email: {str(e)}')


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
      raise Exception('No password reset request found.')

    if record.is_expired():
      raise Exception('Verification code has expired.')

    if record.code != code:
      raise Exception('Incorrect verification code.')

    one_time_token = secrets.token_urlsafe(32)
    record.token = one_time_token
    record.save()

    return VerifyResetCode(message='Verification successful', token=one_time_token)


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
      raise Exception('No password reset request found.')

    if record.token != token:
      raise Exception('Invalid token.')

    try:
      validate_password(new_password)
    except PasswordValidationError as e:
      raise Exception(f'Password error: {" ".join(e.messages)}')

    try:
      user = User.objects.get(email=email)
      user.set_password(new_password)
      user.save()
      record.delete()
      return ResetPassword(message='Password successfully changed.')
    except User.DoesNotExist:
      raise Exception('User not found.')


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
    return UpdateUsername(message='Name successfully updated.', name=name)


class DeleteAccount(graphene.Mutation):
  message = graphene.String()

  @login_required
  def mutate(self, info):
    user = info.context.user
    user.delete()
    return DeleteAccount(message='Account successfully deleted.')


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

""" Validationチェック処理
"""
import re

import email_validator


# ProjectName最大長.
PROJECT_NAME_MAX_LEN = 55
# Email最大長.
EMAIL_MAX_LEN = 64

# Environment値一覧.
ENVIRONMENT_VALUES = [
    "cmn",
    "dev",
    "stg",
    "prd",
]

# ManagementGroups値一覧.
MANAGEMENT_GROUPS_VALUES = [
    "Confidential",
    "NonConfidential",
    "Sandbox",
]

# Permission値一覧.
PERMISSION_VALUES = [
    "admin",
    "developer",
    "operator",
]

# AssignRole値一覧.
ASSIGN_ROLE_VALUES = [
    "owner",
    "contributor",
]


def check_project_name(target_value: str, is_raise: bool = False) -> bool:
    """ProjectNameのバリエーションチェックを行う。

    :param target_value: チェック対象の値
    :param is_raise: True=無効値の場合に例外をraiseする。

    :return bool: チェック結果: True=有効値, False=無効値(is_raise = False時のみ)

    :raise ValueError: 無効値(is_raise = True時のみ)
    """
    is_valid = True
    # 長さチェック.
    if len(target_value) > PROJECT_NAME_MAX_LEN:
        is_valid = False
    # 無効文字チェック.
    if not re.match("^[-_.A-Za-z0-9]+$"):
        is_valid = False
    # 無効値の場合の例外処理.
    if not is_valid and is_raise:
        raise ValueError("Invalid ProjectName")
    return is_valid


def check_environment(target_value: str, is_raise: bool = False) -> bool:
    """Environmentのバリエーションチェックを行う。

    :param target_value: チェック対象の値
    :param is_raise: True=無効値の場合に例外をraiseする。

    :return bool: チェック結果: True=有効値, False=無効値(is_raise = False時のみ)

    :raise ValueError: 無効値(is_raise = True時のみ)
    """
    is_valid = True
    if target_value not in ENVIRONMENT_VALUES:
        is_valid = False
    # 無効値の場合の例外処理.
    if not is_valid and is_raise:
        raise ValueError("Invalid Environment")
    return is_valid


def check_management_groups(target_value: str, is_raise: bool = False) -> bool:
    """ManagementGroupsのバリエーションチェックを行う。

    :param target_value: チェック対象の値
    :param is_raise: True=無効値の場合に例外をraiseする。

    :return bool: チェック結果: True=有効値, False=無効値(is_raise = False時のみ)

    :raise ValueError: 無効値(is_raise = True時のみ)
    """
    is_valid = True
    if target_value not in MANAGEMENT_GROUPS_VALUES:
        is_valid = False
    # 無効値の場合の例外処理.
    if not is_valid and is_raise:
        raise ValueError("Invalid ManagementGroups")
    return is_valid


def check_email(target_value: str, is_raise: bool = False) -> bool:
    """Emailのバリエーションチェックを行う。

    :param target_value: チェック対象の値
    :param is_raise: True=無効値の場合に例外をraiseする。

    :return bool: チェック結果: True=有効値, False=無効値(is_raise = False時のみ)

    :raise ValueError: 無効値(is_raise = True時のみ)
    """
    is_valid = True
    # 長さチェック.
    if len(target_value) > EMAIL_MAX_LEN:
        is_valid = False
    # Email書式チェック.
    try:
        email_validator.validate_email(target_value)
    except ValueError as e:
        is_valid = False
    # 無効値の場合の例外処理.
    if not is_valid and is_raise:
        raise ValueError("Invalid Email")
    return is_valid


def check_emails(target_value: list[str], is_raise: bool = False) -> bool:
    """Emails(Emailリスト)のバリエーションチェックを行う。

    :param target_value: チェック対象の値
    :param is_raise: True=無効値の場合に例外をraiseする。

    :return bool: チェック結果: True=有効値, False=無効値(is_raise = False時のみ)

    :raise ValueError: 無効値(is_raise = True時のみ)
    """
    is_valid = True
    if not target_value:
        # 空の場合は無効値.
        is_valid = False
    else:
        # リスト内の全Emailをチェック.
        for email in target_value:
            if not check_email(email):
                is_valid = False
                break
    # 無効値の場合の例外処理.
    if not is_valid and is_raise:
        raise ValueError("Invalid Emails")
    return is_valid


def check_permission(target_value: str, is_raise: bool = False) -> bool:
    """Permissionのバリエーションチェックを行う。

    :param target_value: チェック対象の値
    :param is_raise: True=無効値の場合に例外をraiseする。

    :return bool: チェック結果: True=有効値, False=無効値(is_raise = False時のみ)

    :raise ValueError: 無効値(is_raise = True時のみ)
    """
    is_valid = True
    if target_value not in PERMISSION_VALUES:
        is_valid = False
    # 無効値の場合の例外処理.
    if not is_valid and is_raise:
        raise ValueError("Invalid Permission")
    return is_valid


def check_assign_role(target_value: str, is_raise: bool = False) -> bool:
    """AssignRoleのバリエーションチェックを行う。

    :param target_value: チェック対象の値
    :param is_raise: True=無効値の場合に例外をraiseする。

    :return bool: チェック結果: True=有効値, False=無効値(is_raise = False時のみ)

    :raise ValueError: 無効値(is_raise = True時のみ)
    """
    is_valid = True
    if target_value not in ASSIGN_ROLE_VALUES:
        is_valid = False
    # 無効値の場合の例外処理.
    if not is_valid and is_raise:
        raise ValueError("Invalid Permission")
    return is_valid

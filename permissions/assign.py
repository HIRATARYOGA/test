"""権限追加処理
"""
import asyncio
import json

import azure.functions as func
import azure.identity

import common.log_util as log_util
from . import perm_common as perm_common

# ログ出力
logger = log_util.get_logger(__name__)


async def _assign_permission(subscription_name: str, permission: str, emails: list[str]):
    """ユーザーをEntraグループへ追加する。

    :param subscription_name: サブスクリプション名(subs-*)
    :param permission: 権限 {admin, developer, operator}
    :param emails: ユーザー名リスト
    """

    # TODO: Validation処理が未実装。

    # Azure認証情報を取得する。
    # ※ DefaultAzureCredentialを用いて、
    #     クライアントシークレット環境変数がある場合は環境変数から、
    #     ManagedIdentityがある場合はManagedIdentityから、
    #     認証情報を取得する。
    credential = azure.identity.DefaultAzureCredential()

    # 対象のEntraグループ名を取得する。
    target_group_name = perm_common.get_entra_group_name_from_subscription_name(
        subscription_name=subscription_name, permission=permission,
    )

    for email in emails:
        # ユーザーIDを取得する。
        user_id = await perm_common.get_user_id(
            credential=credential, username=email,
        )
        logger.debug(f"User {email} ID: {user_id}")

        # 指定ユーザーが所属しているグループ一覧を取得する。
        user_attached_group_names = await perm_common.get_user_attached_group_names(
            credential=credential, user_id=user_id,
        )
        logger.debug(f"UserAttachedGroupNames: {user_attached_group_names}")

        # グループ名->グループIDのdictを作成する。
        group_name_id_dict = await perm_common.get_all_group_name_id_dict(
            credential=credential,
        )
        # logger.debug(f"Group Name->ID Dict: {group_name_id_dict}")
        # logger.debug(f"GroupNames: {list(group_name_id_dict.keys())}")

        # 指定グループの所属ユーザーを取得する。
        group_id = group_name_id_dict[target_group_name]
        group_members = await perm_common.get_group_members(
            credential=credential, group_id=group_id,
        )
        logger.debug(f"Group {group_id} members: {[user.user_principal_name for user in group_members]}")

        # 指定グループにユーザーを追加する。
        await perm_common.attach_user_to_group(
            credential=credential, user_id=user_id, group_id=group_id,
        )

        logger.info(f"User {email} is attached to Group {target_group_name}")

    return


def permissions_assign(req: func.HttpRequest) -> func.HttpResponse:
    """権限追加API

    :param req: HTTPリクエスト情報

    :return HttpResponse: HTTP結果情報
    """
    status_code = 500
    http_res_body = {
        "Message": "Internal server error",
    }
    try:
        req_json = req.get_json()
        subscription_name: str = req_json["SubscriptionName"]
        permission: str = req_json["Permission"]
        emails: list[str] = req_json["Emails"]
        logger.info(f"PermissionsAssign start subs={subscription_name} perm={permission} emails={emails}")

        asyncio.run(_assign_permission(subscription_name, permission, emails))

        logger.info(f"PermissionsAssign success subs={subscription_name} perm={permission} emails={emails}")
        status_code = 200
        http_res_body = {
            "Message": "Permission assign request accepted",
        }
    except ValueError as e:
        logger.error(f"PermissionsAssign ValidationError: {str(e)}", exc_info=e)
        status_code = 400
        http_res_body = {
            "Message": "Validation error or missing parameters",
        }
    except Exception as e:
        logger.error(f"PermissionsAssign Error: {str(e)}", exc_info=e)
        status_code = 500
        http_res_body = {
            "Message": "Internal server error",
        }

    # TODO: 実行結果送信処理が未実装。

    http_res = func.HttpResponse(
        status_code=status_code,
        headers={
            "Content-Type": "application/json",
        },
        body=json.dumps(http_res_body, ensure_ascii=True),
    )
    return http_res

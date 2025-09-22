"""権限追加処理
"""
import asyncio
import datetime
import json
import uuid

import azure.functions as func
import azure.identity
import azure.mgmt.authorization.models
import azure.mgmt.resource.subscriptions
from msgraph.generated.models.group import Group as Group
from msgraph.generated.models.user import User as User

import common.log_util as log_util
from . import perm_common as perm_common

# Assign->PIM有効期限(分)テーブル
PIM_DURATION_TABLE = {
    "owner": 120,
    "contributor": 480,
}

# 所有者ロールID
ROLE_ID_OWNER = "8e3af657-a8ff-443c-a75c-2fe8c4bcb635"
# 共同作成者ロールID
ROLE_ID_CONTRIBUTOR = "b24988ac-6180-42a0-ab88-20f7382dd24c"

# AssignRole->RoleID table
ROLE_ID_TABLE = {
    "owner": ROLE_ID_OWNER,
    "contributor": ROLE_ID_CONTRIBUTOR,
}

# ログ出力
logger = log_util.get_logger(__name__)


async def _elevate_privilege(subscription_name: str, assign_role: str, emails: list[str]):
    """PIMでユーザーに一時的な権限を付与する。

    :param subscription_name: サブスクリプション名(subs-*)
    :param assign_role: 権限 {owner, contributor}
    :param emails: ユーザー名リスト
    """

    # TODO: Validation処理が未実装。

    # Azure認証情報を取得する。
    # ※ DefaultAzureCredentialを用いて、
    #     クライアントシークレット環境変数がある場合は環境変数から、
    #     ManagedIdentityがある場合はManagedIdentityから、
    #     認証情報を取得する。
    credential = azure.identity.DefaultAzureCredential()

    # サブスクリプションIDを取得する。
    subs_client = azure.mgmt.resource.subscriptions.SubscriptionClient(credential=credential)
    subs_list = subs_client.subscriptions.list()
    target_subs = [subs for subs in subs_list if subs.display_name == subscription_name]
    if not target_subs:
        raise ValueError("Subscription is not found")
    subscription_id = target_subs[0].id

    for email in emails:
        # ユーザーIDを取得する。
        user_id = await perm_common.get_user_id(
            credential=credential, username=email,
        )
        logger.debug(f"User {email} ID: {user_id}")

        # Entra IDユーザーが所属するグループ名一覧を取得する。
        group_names = await perm_common.get_user_attached_group_names(credential, user_id)
        logger.debug(f"User {user_id} is in group {group_names}")

        # TODO: グループ判定処理が未実装。

        # 開始日時を作成する。
        pim_duration = PIM_DURATION_TABLE[assign_role]
        JST = datetime.timezone(offset=datetime.timedelta(hours=9), name="JST")
        start_date_time = datetime.datetime.now(tz=JST)
        # 終了日時を作成する。
        end_date_time = start_date_time + datetime.timedelta(minutes=pim_duration)
        logger.debug(f"start={start_date_time.isoformat()} end={end_date_time.isoformat()}")
        # ロール定義IDを作成する。
        role_id = ROLE_ID_TABLE[assign_role]
        role_definition_id = f"/subscriptions/{subscription_id}/providers/Microsoft.Authorization/roleDefinitions/{role_id}"
        logger.debug(f"subs_id={subscription_id} role_id={role_id}")
        # 権限付与先スコープを作成する。
        pim_scope = f"/providers/Microsoft.Subscription/subscriptions/{subscription_id}/"
        # リクエストIDを作成する。
        pim_request_id = uuid.uuid4()
        logger.debug(f"pim_request_id={pim_request_id}")

        # PIM権限付与を実行する。
        auth_client = azure.mgmt.authorization.AuthorizationManagementClient(
            credential=credential,
            subscription_id=subscription_id,
        )
        pim_req_params = azure.mgmt.authorization.models.RoleAssignmentScheduleRequest(
            role_definition_id=role_definition_id,
            principal_id=user_id,
            request_type=azure.mgmt.authorization.models.RequestType.ADMIN_ASSIGN,
            schedule_info=azure.mgmt.authorization.models.RoleAssignmentScheduleRequestPropertiesScheduleInfo(
                start_date_time=start_date_time,
                expiration=azure.mgmt.authorization.models.RoleAssignmentScheduleRequestPropertiesScheduleInfoExpiration(
                    type=azure.mgmt.authorization.models.Type.AFTER_DATE_TIME,
                    end_date_time=end_date_time,
                ),
            ),
        )
        pim_req_result = auth_client.role_assignment_schedule_requests.create(
            scope=pim_scope,
            role_assignment_schedule_request_name=pim_request_id,
            parameters=pim_req_params,
        )
        logger.debug(f"pim_result={pim_req_result}")

        logger.info(f"User {email} permission is elevated to {assign_role}")

    return


def privilege_elevations(req: func.HttpRequest) -> func.HttpResponse:
    """特権昇格API

    :param req: HTTPリクエスト情報

    :return HttpResponse: HTTP結果情報
    """
    status_code = 500
    http_res_body = {
        "Message": "Internal server error",
    }
    try:
        req_json: dict = req.get_json()
        project_name: str = req_json["ProjectName"]
        environment: str = req_json["Environment"]
        assign_role: str = req_json["AssignRole"]
        email: str = req_json["Email"]
        emails: list[str] = [email]
        subscription_name = req_json.get("SubscriptionName", f"subs-{project_name}-{environment}")
        logger.info(f"PrivilegeElevations start subs={subscription_name} role={assign_role} emails={emails}")

        asyncio.run(_elevate_privilege(subscription_name, assign_role, emails))

        logger.info(f"PrivilegeElevations success subs={subscription_name} role={assign_role} emails={emails}")
        status_code = 200
        http_res_body = {
            "Message": "Privilege elevations request accepted",
        }
    except ValueError as e:
        logger.error(f"PrivilegeElevations ValidationError: {str(e)}", exc_info=e)
        status_code = 400
        http_res_body = {
            "Message": "Validation error or missing parameters",
        }
    except Exception as e:
        logger.error(f"PrivilegeElevations Error: {str(e)}", exc_info=e)
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

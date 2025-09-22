import json
import os
import re
import requests

import azure.functions as func
import azure.identity

import common.log_util as log_util


# ログ出力
logger = log_util.get_logger(__name__)


# 許容値
ALLOWED_ENVS = {"cmn", "dev", "stg", "prd"}
ALLOWED_VNET_TYPES = {"private", "public"}


def _get_ado_bearer_from_mi() -> str:
    """Managed Identity から Azure DevOps のアクセストークン(Bearer)を取得する"""
    credential = azure.identity.DefaultAzureCredential()
    resource_id = os.getenv("AZDO_RESOURCE_ID")
    scope = f"{resource_id}/.default"
    token = credential.get_token(scope)
    return token.token


def _looks_like_email(s: str) -> bool:
    """メールアドレス形式チェック"""
    if not s:
        return False
    if len(s) > 254:
        return False
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", s))


def azure_subscription(req: func.HttpRequest) -> func.HttpResponse:
    """Azure DevOps パイプラインを起動する"""
    status_code = 500
    http_res_body = {"Message": "Internal server error"}
    try:
        try:
            body = req.get_json()
        except ValueError:
            status_code = 400
            http_res_body = {"Message": "Invalid or missing JSON body"}
            return func.HttpResponse(
                status_code=status_code,
                headers={"Content-Type": "application/json"},
                body=json.dumps(http_res_body, ensure_ascii=True),
            )

        if not isinstance(body, dict):
            status_code = 400
            http_res_body = {"Message": "JSON must be an object"}
            return func.HttpResponse(
                status_code=status_code,
                headers={"Content-Type": "application/json"},
                body=json.dumps(http_res_body, ensure_ascii=True),
            )

        # 入力値の取得
        project_name_raw = body.get("ProjectName")
        environment_id_raw = body.get("Environment")
        email_raw = body.get("Email")
        vnet_type_raw = body.get("VNetType")
        management_group_id_raw = body.get("ManagementGroups")

        project_name = project_name_raw.strip() if isinstance(
            project_name_raw, str) else None
        environment_id = environment_id_raw.strip() if isinstance(
            environment_id_raw, str) else None
        email = email_raw.strip() if isinstance(email_raw, str) else None
        vnet_type = (vnet_type_raw or "").strip().lower()
        management_group_id = management_group_id_raw.strip(
        ) if isinstance(management_group_id_raw, str) else None

        # 必須/形式チェック
        if not project_name:
            raise ValueError("Missing required field: ProjectName")
        if not environment_id:
            raise ValueError("Missing required field: Environment")
        env_lower = environment_id.lower()
        if env_lower not in ALLOWED_ENVS:
            raise ValueError(
                "Invalid Environment. Allowed values are: cmn, dev, stg, prd")
        if not email:
            raise ValueError("Missing required field: Email")
        if not _looks_like_email(email):
            raise ValueError("Invalid email format")
        if not management_group_id:
            raise ValueError("Missing required field: ManagementGroups")
        if not vnet_type:
            raise ValueError("Missing required field: VNetType")
        if vnet_type not in ALLOWED_VNET_TYPES:
            raise ValueError(
                "Invalid VNetType. Allowed values are: private, public")

        # ルーティングのブランチ指定（省略時 main）
        branch = body.get("branch", "refs/heads/main")

        # パイプライン実行準備
        org = os.environ.get("AZDO_ORG")
        proj = os.environ.get("AZDO_PROJECT")

        # パイプラインID定義（環境変数から取得）
        pipelineID_public = os.environ.get("AZDO_PIPELINE_ID_PUBLIC")
        pipelineID_private = os.environ.get("AZDO_PIPELINE_ID_PRIVATE")

        # VNetTypeに基づいてパイプラインIDを選択
        if vnet_type == "public":
            selected_pid = pipelineID_public
        elif vnet_type == "private":
            selected_pid = pipelineID_private
        else:
            # 念のため（バリデーション済みなので到達しない）
            raise ValueError(f"Unexpected VNetType: {vnet_type}")

        if org and proj and selected_pid:
            url = f"https://dev.azure.com/{org}/{proj}/_apis/pipelines/{selected_pid}/runs?api-version=7.0"
            template_params = {
                "project_name": project_name,
                "environment_id": env_lower,
                "email": email,
                "management_group_id": management_group_id,
            }
            payload = {
                "resources": {"repositories": {"self": {"refName": branch}}},
                "templateParameters": template_params,
            }

            bearer = _get_ado_bearer_from_mi()
            headers = {"Authorization": f"Bearer {bearer}",
                       "Content-Type": "application/json"}

            logger.info(
                f"[azure_subscription] POST {url} branch={branch} templateParameters={json.dumps(template_params, ensure_ascii=False)}"
            )

            resp = requests.post(url, headers=headers,
                                 data=json.dumps(payload), timeout=30)

            if resp.status_code in (200, 201, 202):
                status_code = 200
                http_res_body = {
                    "Message": "Azure subscription request accepted"}
            else:
                status_code = 500
                http_res_body = {"Message": "Pipeline start failed"}
                try:
                    logger.error(
                        f"Pipeline failed status={resp.status_code} body={resp.text[:500] if resp.text else ''}")
                except Exception:
                    pass
        else:
            # パイプライン設定不足
            status_code = 200
            http_res_body = {
                "Message": "Request accepted (pipeline not executed: missing configuration)"}

    except ValueError as e:
        logger.error(
            f"AzureSubscription ValidationError: {str(e)}", exc_info=e)
        status_code = 400
        http_res_body = {"Message": "Validation error or missing parameters"}
    except Exception as e:
        logger.error(f"AzureSubscription Error: {str(e)}", exc_info=e)
        status_code = 500
        http_res_body = {"Message": "Internal server error"}

    return func.HttpResponse(
        status_code=status_code,
        headers={"Content-Type": "application/json"},
        body=json.dumps(http_res_body, ensure_ascii=True),
    )

"""権限追加削除共通処理
"""
import re

import msgraph
from msgraph.generated.models.directory_object_collection_response import DirectoryObjectCollectionResponse
from msgraph.generated.models.group import Group as Group
from msgraph.generated.models.reference_create import ReferenceCreate as ReferenceCreate
from msgraph.generated.models.user import User as User

import azure.core.credentials
import azure.identity
import requests


def get_entra_group_name_from_subscription_name(subscription_name: str, permission: str) -> str:
    """サブスクリプション名からEntraグループ名を取得する。

    :param subscription_name: サブスクリプション名
    :param permission: 権限 {admin, developer, operator}

    :return str: Entraグループ名
    """
    pj_usage_env = re.sub(r'^subs-', '', subscription_name)
    group_name = f"azure-{pj_usage_env}-group-{permission}"
    return group_name


async def get_user_info(credential, user_id: str) -> User | None:
    """Entra IDユーザー情報を取得する。
    Args:
        credential: Azure認証情報
        user_id: ユーザーID(UserPrincipalNameも可能)
    Returns:
        ユーザー情報
    """
    # GraphAPIサービスクライアントを取得する。
    graph_client = msgraph.GraphServiceClient(credentials=credential)
    # 指定ユーザーのユーザー情報を取得する。
    user_info = await graph_client.users.by_user_id(user_id).get()
    return user_info


async def get_user_attached_group_infos(credential, user_id: str) -> DirectoryObjectCollectionResponse | None:
    """Entra IDユーザーが所属しているグループの情報一覧を取得する。
    Args:
        credential: Azure認証情報
        user_id: ユーザーID(UserPrincipalNameも可能)
    Returns:
        グループ情報一覧
    """
    # GraphAPIサービスクライアントを取得する。
    graph_client = msgraph.GraphServiceClient(credentials=credential)
    # 指定ユーザーが所属しているグループ一覧を取得する。
    group_infos = await graph_client.users.by_user_id(user_id).member_of.get()
    return group_infos


async def get_all_group_infos(credential) -> list[Group]:
    """全てのEntraグループの情報一覧を取得する。
    Args:
        credential: Azure認証情報
    Returns:
        グループ情報一覧
    """
    # GraphAPIサービスクライアントを取得する。
    graph_client = msgraph.GraphServiceClient(credentials=credential)
    # 全グループの情報を取得する。
    group_collection = await graph_client.groups.get()
    group_infos = list(group_collection.value)
    return group_infos


async def get_group_members(credential, group_id: str) -> list[User]:
    """指定Entraグループに所属しているメンバー（ユーザー）情報を取得する。
    Args:
        credentail: Azure認証情報
        group_id: 対象EntraグループID
    Returns:
        メンバー情報一覧
    """
    # GraphAPIサービスクライアントを取得する。
    graph_client = msgraph.GraphServiceClient(credentials=credential)
    # グループ内メンバーの一覧を取得する。
    group_members = await graph_client.groups.by_group_id(group_id).members.get()
    users = list(user for user in group_members.value)
    return users


async def attach_user_to_group(credential, user_id: str, group_id: str):
    """Entraユーザーをグループに追加する。
    Args:
        credential: Azure認証情報
        user_id: EntraユーザーID
        user_id: EntraグループID
    """
    # GraphAPIサービスクライアントを取得する。
    graph_client = msgraph.GraphServiceClient(credentials=credential)
    # 指定グループからユーザーを削除する。
    user_ref = ReferenceCreate(odata_id=f"https://graph.microsoft.com/v1.0/directoryObjects/{user_id}")
    await graph_client.groups.by_group_id(group_id).members.ref.post(user_ref)
    return


async def detach_user_from_group(credential, user_id: str, group_id: str):
    """Entraユーザーをグループから削除する。
    Args:
        credential: Azure認証情報
        user_id: EntraユーザーID
        user_id: EntraグループID
    """
    # GraphAPIサービスクライアントを取得する。
    graph_client = msgraph.GraphServiceClient(credentials=credential)
    # 指定グループからユーザーを削除する。
    await graph_client.groups.by_group_id(group_id).members.by_directory_object_id(user_id).ref.delete()
    return


async def get_user_id(credential, username: str) -> str:
    """Entra IDユーザーIDを取得する。
    Args:
        credential: Azure認証情報
        user_id: ユーザー名(UserPrincipalName)
    Returns:
        ユーザーID
    """
    user = await get_user_info(credential=credential, user_id=username)
    user_id = user.id if user and user.id else None
    return user_id


async def get_user_attached_group_names(credential, user_id: str) -> list[str]:
    """Entra IDユーザーが所属しているグループの名前一覧を取得する。
    Args:
        credential: Azure認証情報
        user_id: ユーザーID(UserPrincipalNameも可能)
    Returns:
        グループ名一覧
    """
    # 指定ユーザーが所属しているグループ一覧を取得する。
    groups = await get_user_attached_group_infos(credential=credential, user_id=user_id)
    # Azureグループ名の一覧を生成する。
    group_names: list[str] = []
    if groups and groups.value:
        for group in groups.value:
            if group.odata_type == Group.odata_type and group.display_name:
                group_names.append(group.display_name)

    return group_names


async def get_all_group_name_id_dict(credential) -> dict[str, str]:
    """全てのEntraグループ名->グループIDのdictをを取得する。
    Args:
        credential: Azure認証情報
    Returns:
        グループ名->グループIDのdict
    """
    groups = await get_all_group_infos(credential=credential)
    # グループ名->グループIDのdictを作成する。
    group_name_id_dict = {group.display_name: group.id for group in groups}
    return group_name_id_dict


def send_email(
        credential: azure.identity.ManagedIdentityCredential,
        sender: str, recipient: str, subject: str,
        content: str | bytes, content_type: str = "Text",
    ) -> requests.Response:
    """Eメールを送信する。

    :param credential: Azure認証情報
    :param sender: 送信元アドレス（ライセンスのあるユーザーのUPN）
    :param recipient: 宛先アドレス
    :param subject: 件名
    :param content: 本文
    :param content_type: 本文の形式 {"Text"}

    :return requests.Response: Eメール送信要求の応答
    """
    # Microsoft Graph エンドポイント
    GRAPH_URL = "https://graph.microsoft.com/v1.0"
    # トークンを取得
    token: azure.core.credentials.AccessToken = credential.get_token("https://graph.microsoft.com/.default")
    # メール送信リクエスト
    url = f"{GRAPH_URL}/users/{sender}/sendMail"
    headers = {"Authorization": f"Bearer {token.token}", "Content-Type": "application/json"}
    body = {
        "message": {
            "subject": subject or "",
            "body": {
                "contentType": content_type or "",
                "content": content or "",
            },
            "toRecipients": [
                {"emailAddress": {"address": recipient}},
            ],
        },
    }
    resp = requests.post(url, headers=headers, json=body)
    return resp

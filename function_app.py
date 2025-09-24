#2
import azure.functions as func


import permissions.assign
import permissions.elevations
import permissions.revoke
import azure_subscription.azure_subscription as azure_subscription

app = func.FunctionApp()  # Functionアプリ本体（エンドポイントを登録）


# ========= サブスクリプション自動作成 =========


@app.route(route="azure/subscription", auth_level=func.AuthLevel.ANONYMOUS, methods=["POST"])
def azure_subscription_route(req: func.HttpRequest) -> func.HttpResponse:
    """Azure サブスクリプション API
    """
    return azure_subscription.azure_subscription(req)


# ========= 権限追加・削除 =========


@app.route(route="azure/permissions/assign", auth_level=func.AuthLevel.ANONYMOUS, methods=["POST"])
def permissions_assign(req: func.HttpRequest) -> func.HttpResponse:
    """権限追加API
    """
    return permissions.assign.permissions_assign(req)


@app.route(route="azure/permissions/revoke", auth_level=func.AuthLevel.ANONYMOUS, methods=["POST"])
def permissions_revoke(req: func.HttpRequest) -> func.HttpResponse:
    """権限削除API
    """
    return permissions.revoke.permissions_revoke(req)


# ========= 特権昇格 =========


@app.route(route="azure/privilege/elevations", auth_level=func.AuthLevel.ANONYMOUS, methods=["POST"])
def privilege_elevations(req: func.HttpRequest) -> func.HttpResponse:
    """特権昇格API
    """
    return permissions.elevations.privilege_elevations(req)

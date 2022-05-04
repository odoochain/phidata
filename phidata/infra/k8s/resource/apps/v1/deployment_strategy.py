from typing import Union
from typing_extensions import Literal

from kubernetes.client.models.v1_deployment_strategy import V1DeploymentStrategy
from kubernetes.client.models.v1_rolling_update_deployment import (
    V1RollingUpdateDeployment,
)
from pydantic import Field

from phidata.infra.k8s.resource.base import K8sObject


class RollingUpdateDeployment(K8sObject):
    """
    # https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#rollingupdatedeployment-v1-apps
    """

    resource_type: str = "RollingUpdateDeployment"

    max_surge: Union[int, str] = Field(..., alias="maxSurge")
    max_unavailable: Union[int, str] = Field(..., alias="maxUnavailable")

    def get_k8s_object(self) -> V1RollingUpdateDeployment:

        # Return a V1RollingUpdateDeployment object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_rolling_update_deployment.py
        _v1_rolling_update_deployment = V1RollingUpdateDeployment(
            max_surge=self.max_surge,
            max_unavailable=self.max_unavailable,
        )
        return _v1_rolling_update_deployment


class DeploymentStrategy(K8sObject):
    """
    # https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#deploymentstrategy-v1-apps
    """

    resource_type: str = "DeploymentStrategy"

    rolling_update: RollingUpdateDeployment = Field(..., alias="rollingUpdate")
    type: Literal["Recreate", "RollingUpdate"] = "RollingUpdate"

    def get_k8s_object(self) -> V1DeploymentStrategy:

        # Return a V1DeploymentStrategy object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_deployment_strategy.py
        _v1_deployment_strategy = V1DeploymentStrategy(
            rolling_update=self.rolling_update.get_k8s_object(),
            type=self.type,
        )
        return _v1_deployment_strategy

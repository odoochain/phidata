from collections import OrderedDict
from pathlib import Path
from typing import Optional, Dict, List, Union
from typing_extensions import Literal

from phidata.app.db import DbApp, DbAppArgs
from phidata.infra.aws.resource.ec2.volume import EbsVolume
from phidata.infra.docker.resource.container import DockerContainer
from phidata.infra.docker.resource.group import (
    DockerResourceGroup,
    DockerBuildContext,
)
from phidata.infra.docker.resource.network import DockerNetwork
from phidata.infra.k8s.create.apps.v1.deployment import CreateDeployment, RestartPolicy
from phidata.infra.k8s.create.common.port import CreatePort
from phidata.infra.k8s.create.core.v1.config_map import CreateConfigMap
from phidata.infra.k8s.create.core.v1.container import CreateContainer, ImagePullPolicy
from phidata.infra.k8s.create.core.v1.secret import CreateSecret
from phidata.infra.k8s.create.core.v1.service import CreateService, ServiceType
from phidata.infra.k8s.create.core.v1.volume import (
    CreateVolume,
    HostPathVolumeSource,
    AwsElasticBlockStoreVolumeSource,
    VolumeType,
)
from phidata.infra.k8s.create.group import CreateK8sResourceGroup
from phidata.infra.k8s.resource.group import (
    K8sResourceGroup,
    K8sBuildContext,
)
from phidata.utils.cli_console import print_error, print_info, print_warning
from phidata.utils.common import (
    get_image_str,
    get_default_container_name,
    get_default_configmap_name,
    get_default_secret_name,
    get_default_service_name,
    get_default_volume_name,
    get_default_deploy_name,
    get_default_pod_name,
)
from phidata.utils.enums import ExtendedEnum
from phidata.utils.log import logger


class RedisVolumeType(ExtendedEnum):
    EMPTY_DIR = "EMPTY_DIR"
    HOST_PATH = "HOST_PATH"
    PERSISTENT_VOLUME = "PERSISTENT_VOLUME"
    AWS_EBS = "AWS_EBS"


class RedisArgs(DbAppArgs):
    name: str = "redis"
    version: str = "1"
    enabled: bool = True

    # Image args
    image_name: str = "redis"
    image_tag: str = "6.2.6"
    entrypoint: Optional[Union[str, List]] = None
    command: Optional[Union[str, List]] = None

    # Configure redis
    # Provide REDIS_PASSWORD as redis_password or REDIS_PASSWORD in secrets_file
    redis_password: Optional[str] = None
    # Provide REDIS_SCHEMA as redis_schema or REDIS_SCHEMA in secrets_file
    redis_schema: Optional[str] = None
    redis_driver: str = "redis"
    logging_level: Literal[
        "debug",
        "info",
        "warning",
        "error",
        "critical",
    ] = "debug"

    # Configure the volume
    create_volume: bool = True
    volume_type: RedisVolumeType = RedisVolumeType.EMPTY_DIR
    volume_name: Optional[str] = None
    # Container path to mount the postgres volume
    # should be the parent directory of redisdata
    volume_container_path: str = "/data"
    # Host path to mount the postgres volume
    # If volume_type = RedisVolumeType.HOST_PATH
    volume_host_path: Optional[Path] = None
    # EbsVolume if volume_type = PostgresVolumeType.AWS_EBS
    ebs_volume: Optional[EbsVolume] = None
    # EbsVolume region is used to determine the ebs_volume_id
    # and add topology region selectors
    ebs_volume_region: Optional[str] = None
    # Provide Ebs Volume-id manually
    ebs_volume_id: Optional[str] = None
    # Add topology az selectors
    ebs_volume_az: Optional[str] = None
    # Add NodeSelectors to Pods, so they are scheduled in the same
    # region and zone as the ebs_volume
    schedule_pods_in_ebs_topology: bool = True

    # Configure the container
    container_name: Optional[str] = None
    image_pull_policy: ImagePullPolicy = ImagePullPolicy.IF_NOT_PRESENT
    container_port: int = 6379
    # Only used by the K8sContainer
    container_port_name: str = "redis"
    # Only used by the DockerContainer
    container_host_port: int = 6379
    container_detach: bool = True
    container_auto_remove: bool = True
    container_remove: bool = True

    # Add env variables to container env
    env: Optional[Dict[str, str]] = None
    # Read env variables from a file in yaml format
    env_file: Optional[Path] = None
    # Configure the ConfigMap used for env variables that are not Secret
    config_map_name: Optional[str] = None
    # Configure the Secret used for env variables that are Secret
    secret_name: Optional[str] = None
    # Read secrets from a file in yaml format
    secrets_file: Optional[Path] = None

    # Configure the deployment
    deploy_name: Optional[str] = None
    pod_name: Optional[str] = None
    replicas: int = 1
    pod_node_selector: Optional[Dict[str, str]] = None
    restart_policy: RestartPolicy = RestartPolicy.ALWAYS
    termination_grace_period_seconds: Optional[int] = None

    # Configure the service
    service_name: Optional[str] = None
    service_type: Optional[ServiceType] = None
    # The port that will be exposed by the service.
    service_port: int = 6379
    # The node_port that will be exposed by the service if service_type = ServiceType.NODE_PORT
    node_port: Optional[int] = None
    # The target_port is the port to access on the pods targeted by the service.
    # It can be the port number or port name on the pod.
    target_port: Optional[Union[str, int]] = None


class Redis(DbApp):
    def __init__(
        self,
        name: str = "redis",
        version: str = "1",
        enabled: bool = True,
        # Image args,
        image_name: str = "redis",
        image_tag: str = "6.2.6",
        entrypoint: Optional[Union[str, List]] = None,
        command: Optional[Union[str, List]] = None,
        # Configure redis,
        # Provide REDIS_PASSWORD as redis_password or REDIS_PASSWORD in secrets_file,
        redis_password: Optional[str] = None,
        # Provide REDIS_SCHEMA as redis_schema or REDIS_SCHEMA in secrets_file,
        redis_schema: Optional[str] = None,
        redis_driver: str = "redis",
        logging_level: Literal[
            "debug",
            "info",
            "warning",
            "error",
            "critical",
        ] = "debug",
        # Configure the volume,
        create_volume: bool = True,
        volume_type: RedisVolumeType = RedisVolumeType.EMPTY_DIR,
        volume_name: Optional[str] = None,
        # Container path to mount the postgres volume,
        # should be the parent directory of redisdata,
        volume_container_path: str = "/data",
        # Host path to mount the postgres volume,
        # If volume_type = RedisVolumeType.HOST_PATH,
        volume_host_path: Optional[Path] = None,
        # EbsVolume if volume_type = PostgresVolumeType.AWS_EBS,
        ebs_volume: Optional[EbsVolume] = None,
        # EbsVolume region is used to determine the ebs_volume_id,
        # and add topology region selectors,
        ebs_volume_region: Optional[str] = None,
        # Provide Ebs Volume-id manually,
        ebs_volume_id: Optional[str] = None,
        # Add topology az selectors,
        ebs_volume_az: Optional[str] = None,
        # Add NodeSelectors to Pods, so they are scheduled in the same,
        # region and zone as the ebs_volume,
        schedule_pods_in_ebs_topology: bool = True,
        # Configure the container,
        container_name: Optional[str] = None,
        image_pull_policy: ImagePullPolicy = ImagePullPolicy.IF_NOT_PRESENT,
        container_port: int = 6379,
        # Only used by the K8sContainer,
        container_port_name: str = "redis",
        # Only used by the DockerContainer,
        container_host_port: int = 6379,
        container_detach: bool = True,
        container_auto_remove: bool = True,
        container_remove: bool = True,
        # Add env variables to container env,
        env: Optional[Dict[str, str]] = None,
        # Read env variables from a file in yaml format,
        env_file: Optional[Path] = None,
        # Configure the ConfigMap used for env variables that are not Secret,
        config_map_name: Optional[str] = None,
        # Configure the Secret used for env variables that are Secret,
        secret_name: Optional[str] = None,
        # Read secrets from a file in yaml format,
        secrets_file: Optional[Path] = None,
        # Configure the deployment,
        deploy_name: Optional[str] = None,
        pod_name: Optional[str] = None,
        replicas: int = 1,
        pod_node_selector: Optional[Dict[str, str]] = None,
        restart_policy: RestartPolicy = RestartPolicy.ALWAYS,
        termination_grace_period_seconds: Optional[int] = None,
        # Configure the service,
        service_name: Optional[str] = None,
        service_type: Optional[ServiceType] = None,
        # The port that will be exposed by the service.,
        service_port: int = 6379,
        # The node_port that will be exposed by the service if service_type = ServiceType.NODE_PORT,
        node_port: Optional[int] = None,
        # The target_port is the port to access on the pods targeted by the service.,
        # It can be the port number or port name on the pod.,
        target_port: Optional[Union[str, int]] = None,
        # Additional args
        # If True, skip resource creation if active resources with the same name exist.
        use_cache: bool = True,
        # If True, log extra debug messages
        use_verbose_logs: bool = False,
    ):
        super().__init__()
        try:
            self.args: RedisArgs = RedisArgs(
                name=name,
                version=version,
                enabled=enabled,
                image_name=image_name,
                image_tag=image_tag,
                entrypoint=entrypoint,
                command=command,
                redis_password=redis_password,
                redis_schema=redis_schema,
                redis_driver=redis_driver,
                logging_level=logging_level,
                create_volume=create_volume,
                volume_type=volume_type,
                volume_name=volume_name,
                volume_container_path=volume_container_path,
                volume_host_path=volume_host_path,
                ebs_volume=ebs_volume,
                ebs_volume_region=ebs_volume_region,
                ebs_volume_id=ebs_volume_id,
                ebs_volume_az=ebs_volume_az,
                schedule_pods_in_ebs_topology=schedule_pods_in_ebs_topology,
                container_name=container_name,
                image_pull_policy=image_pull_policy,
                container_port=container_port,
                container_port_name=container_port_name,
                container_host_port=container_host_port,
                container_detach=container_detach,
                container_auto_remove=container_auto_remove,
                container_remove=container_remove,
                env=env,
                env_file=env_file,
                config_map_name=config_map_name,
                secret_name=secret_name,
                secrets_file=secrets_file,
                deploy_name=deploy_name,
                pod_name=pod_name,
                replicas=replicas,
                pod_node_selector=pod_node_selector,
                restart_policy=restart_policy,
                termination_grace_period_seconds=termination_grace_period_seconds,
                service_name=service_name,
                service_type=service_type,
                service_port=service_port,
                node_port=node_port,
                target_port=target_port,
                use_cache=use_cache,
                use_verbose_logs=use_verbose_logs,
            )
        except Exception:
            logger.error(f"Args for {self.__class__.__name__} are not valid")
            raise

    def get_container_name(self) -> str:
        return self.args.container_name or get_default_container_name(self.args.name)

    def get_service_name(self) -> str:
        return self.args.service_name or get_default_service_name(self.args.name)

    def get_service_port(self) -> int:
        return self.args.service_port

    def get_env_data_from_file(self) -> Optional[Dict[str, str]]:
        import yaml

        env_file_path = self.args.env_file
        if (
            env_file_path is not None
            and env_file_path.exists()
            and env_file_path.is_file()
        ):
            # logger.debug(f"Reading {env_file_path}")
            env_data_from_file = yaml.safe_load(env_file_path.read_text())
            if env_data_from_file is not None and isinstance(env_data_from_file, dict):
                return env_data_from_file
            else:
                print_error(f"Invalid env_file: {env_file_path}")
        return None

    def get_secret_data_from_file(self) -> Optional[Dict[str, str]]:
        import yaml

        secrets_file_path = self.args.secrets_file
        if (
            secrets_file_path is not None
            and secrets_file_path.exists()
            and secrets_file_path.is_file()
        ):
            # logger.debug(f"Reading {secrets_file_path}")
            secret_data_from_file = yaml.safe_load(secrets_file_path.read_text())
            if secret_data_from_file is not None and isinstance(
                secret_data_from_file, dict
            ):
                return secret_data_from_file
            else:
                print_error(f"Invalid secrets_file: {secrets_file_path}")
        return None

    def get_db_password(self) -> Optional[str]:
        redis_password_var: Optional[str] = self.args.db_password if self.args else None
        if redis_password_var is None and self.args.secrets_file is not None:
            # read from secrets_file
            logger.debug(f"Reading REDIS_PASSWORD from secrets_file")
            secret_data_from_file = self.get_secret_data_from_file()
            if secret_data_from_file is not None:
                redis_password_var = secret_data_from_file.get(
                    "REDIS_PASSWORD", redis_password_var
                )
        return redis_password_var

    def get_db_schema(self) -> Optional[str]:
        redis_schema_var: Optional[str] = self.args.db_schema if self.args else None
        if redis_schema_var is None and self.args.secrets_file is not None:
            # read from env_file
            logger.debug(f"Reading REDIS_SCHEMA from secrets_file")
            secret_data_from_file = self.get_secret_data_from_file()
            if secret_data_from_file is not None:
                redis_schema_var = secret_data_from_file.get(
                    "REDIS_SCHEMA", redis_schema_var
                )
        return redis_schema_var

    def get_db_driver(self) -> Optional[str]:
        return self.args.redis_driver if self.args else "redis"

    def get_db_host_local(self) -> Optional[str]:
        return "localhost"

    def get_db_port_local(self) -> Optional[int]:
        return self.args.container_host_port if self.args else None

    def get_db_host_docker(self) -> Optional[str]:
        return self.get_container_name()

    def get_db_port_docker(self) -> Optional[int]:
        return self.args.container_port if self.args else None

    def get_db_host_k8s(self) -> Optional[str]:
        return self.get_service_name()

    def get_db_port_k8s(self) -> Optional[int]:
        return self.get_service_port()

    def get_db_connection_url_local(self) -> Optional[str]:
        password = self.get_db_password()
        password_str = f"{password}@" if password else ""
        schema = self.get_db_schema()
        driver = self.get_db_driver()
        host = self.get_db_host_local()
        port = self.get_db_port_local()
        return f"{driver}://{password_str}@{host}:{port}/{schema}"

    def get_db_connection_url_docker(self) -> Optional[str]:
        password = self.get_db_password()
        password_str = f"{password}@" if password else ""
        schema = self.get_db_schema()
        driver = self.get_db_driver()
        host = self.get_db_host_docker()
        port = self.get_db_port_docker()
        return f"{driver}://{password_str}@{host}:{port}/{schema}"

    def get_db_connection_url_k8s(self) -> Optional[str]:
        password = self.get_db_password()
        password_str = f"{password}@" if password else ""
        schema = self.get_db_schema()
        driver = self.get_db_driver()
        host = self.get_db_host_k8s()
        port = self.get_db_port_k8s()
        return f"{driver}://{password_str}@{host}:{port}/{schema}"

    ######################################################
    ## Docker Resources
    ######################################################

    def get_docker_rg(
        self, docker_build_context: DockerBuildContext
    ) -> Optional[DockerResourceGroup]:

        app_name = self.args.name
        logger.debug(f"Building {app_name} DockerResourceGroup")

        # Container Environment
        container_env: Dict[str, str] = {}

        # Update the container env using env_file
        env_data_from_file = self.get_env_data_from_file()
        if env_data_from_file is not None:
            container_env.update(env_data_from_file)

        # Update the container env using secrets_file
        secret_data_from_file = self.get_secret_data_from_file()
        if secret_data_from_file is not None:
            container_env.update(secret_data_from_file)

        # Update the container env with user provided env
        if self.args.env is not None and isinstance(self.args.env, dict):
            container_env.update(self.args.env)

        # Container Volumes
        container_volumes = {}
        if self.args.create_volume:
            if self.args.volume_type == RedisVolumeType.EMPTY_DIR:
                volume_name = self.args.volume_name or get_default_volume_name(app_name)
                container_volumes[volume_name] = {
                    "bind": self.args.volume_container_path,
                    "mode": "rw",
                }
            elif self.args.volume_type == RedisVolumeType.HOST_PATH:
                if self.args.volume_host_path is not None:
                    volume_host_path_str = str(self.args.volume_host_path)
                    container_volumes[volume_host_path_str] = {
                        "bind": self.args.volume_container_path,
                        "mode": "rw",
                    }
                else:
                    print_error("Redis: volume_host_path not provided")
                    return None
            else:
                print_error(f"{self.args.volume_type.value} not supported")
                return None

        # Container Ports
        container_ports: Dict[str, int] = {
            str(self.args.container_port): self.args.container_host_port,
        }

        # Create the container
        docker_container = DockerContainer(
            name=self.get_container_name(),
            image=get_image_str(self.args.image_name, self.args.image_tag),
            entrypoint=self.args.entrypoint,
            command=self.args.command,
            detach=self.args.container_detach,
            auto_remove=self.args.container_auto_remove,
            remove=self.args.container_remove,
            stdin_open=True,
            tty=True,
            environment=container_env,
            network=docker_build_context.network,
            ports=container_ports,
            volumes=container_volumes,
            use_cache=self.args.use_cache,
            use_verbose_logs=self.args.use_verbose_logs,
        )

        docker_rg = DockerResourceGroup(
            name=app_name,
            enabled=self.args.enabled,
            network=DockerNetwork(name=docker_build_context.network),
            containers=[docker_container],
        )
        return docker_rg

    def init_docker_resource_groups(
        self, docker_build_context: DockerBuildContext
    ) -> None:
        docker_rg = self.get_docker_rg(docker_build_context)
        if docker_rg is not None:
            if self.docker_resource_groups is None:
                self.docker_resource_groups = OrderedDict()
            self.docker_resource_groups[docker_rg.name] = docker_rg

    ######################################################
    ## K8s Resources
    ######################################################

    def get_k8s_rg(
        self, k8s_build_context: K8sBuildContext
    ) -> Optional[K8sResourceGroup]:

        app_name = self.args.name
        logger.debug(f"Building {app_name} K8sResourceGroup")

        # Container Environment
        container_env: Dict[str, str] = {}

        # Update the container env using env_file
        env_data_from_file = self.get_env_data_from_file()
        if env_data_from_file is not None:
            container_env.update(env_data_from_file)
        # Update the container env with user provided env
        if self.args.env is not None and isinstance(self.args.env, dict):
            container_env.update(self.args.env)
        # Create a ConfigMap to set the container env variables which are not Secret
        container_env_cm = CreateConfigMap(
            cm_name=self.args.config_map_name or get_default_configmap_name(app_name),
            app_name=app_name,
            data=container_env,
        )

        # Create a Secret to set the container env variables which are Secret
        container_env_secret: Optional[CreateSecret] = None
        secret_data_from_file = self.get_secret_data_from_file()
        if secret_data_from_file is not None:
            container_env_secret = CreateSecret(
                secret_name=self.args.secret_name or get_default_secret_name(app_name),
                app_name=app_name,
                string_data=secret_data_from_file,
            )

        # Container Volumes
        container_volumes = []
        # Add NodeSelectors to Pods in case we create az sensitive volumes
        pod_node_selector: Optional[Dict[str, str]] = self.args.pod_node_selector
        if self.args.create_volume:
            volume_name = self.args.volume_name or get_default_volume_name(app_name)
            if self.args.volume_type == RedisVolumeType.EMPTY_DIR:
                redis_volume = CreateVolume(
                    volume_name=volume_name,
                    app_name=app_name,
                    mount_path=self.args.volume_container_path,
                    volume_type=VolumeType.EMPTY_DIR,
                )
                container_volumes.append(redis_volume)
            elif self.args.volume_type == RedisVolumeType.HOST_PATH:
                if self.args.volume_host_path is not None:
                    volume_host_path_str = str(self.args.volume_host_path)
                    redis_volume = CreateVolume(
                        volume_name=volume_name,
                        app_name=app_name,
                        mount_path=self.args.volume_container_path,
                        volume_type=VolumeType.HOST_PATH,
                        host_path=HostPathVolumeSource(
                            path=volume_host_path_str,
                        ),
                    )
                    container_volumes.append(redis_volume)
                else:
                    print_error("Redis: volume_host_path not provided")
                    return None
            elif self.args.volume_type == RedisVolumeType.AWS_EBS:
                if (
                    self.args.ebs_volume_id is not None
                    or self.args.ebs_volume is not None
                ):
                    ebs_volume_id = self.args.ebs_volume_id
                    if ebs_volume_id is None and self.args.ebs_volume is not None:
                        ebs_volume_id = self.args.ebs_volume.get_volume_id(
                            aws_region=self.args.ebs_volume_region
                        )
                    logger.debug(f"ebs_volume_id: {ebs_volume_id}")

                    redis_volume = CreateVolume(
                        volume_name=volume_name,
                        app_name=app_name,
                        mount_path=self.args.volume_container_path,
                        volume_type=VolumeType.AWS_EBS,
                        aws_ebs=AwsElasticBlockStoreVolumeSource(
                            volume_id=ebs_volume_id,
                        ),
                    )
                    container_volumes.append(redis_volume)
                    if self.args.schedule_pods_in_ebs_topology:
                        if pod_node_selector is None:
                            pod_node_selector = {}

                        # Add NodeSelectors to Pods, so they are scheduled in the same
                        # region and zone as the ebs_volume
                        # https://kubernetes.io/docs/reference/labels-annotations-taints/#topologykubernetesiozone
                        ebs_region = self.args.ebs_volume_region
                        if ebs_region is not None:
                            pod_node_selector[
                                "topology.kubernetes.io/region"
                            ] = ebs_region

                        ebs_az = self.args.ebs_volume_az
                        if ebs_az is None and self.args.ebs_volume is not None:
                            ebs_az = self.args.ebs_volume.availability_zone
                        if ebs_az is not None:
                            pod_node_selector["topology.kubernetes.io/zone"] = ebs_az
                else:
                    print_error("Redis: ebs_volume not provided")
                    return None
            else:
                print_error(f"{self.args.volume_type.value} not supported")
                return None

        # Create the ports to open
        container_port = CreatePort(
            name=self.args.container_port_name,
            container_port=self.args.container_port,
            service_port=self.args.service_port,
            target_port=self.args.target_port or self.args.container_port_name,
        )

        # If ServiceType == NODE_PORT then validate self.args.node_port is available
        if self.args.service_type == ServiceType.NODE_PORT:
            if (
                self.args.node_port is None
                or self.args.node_port < 30000
                or self.args.node_port > 32767
            ):
                print_error(f"NodePort: {self.args.node_port} invalid")
                print_error(f"Skipping this service")
                return None
            else:
                container_port.node_port = self.args.node_port
        # If ServiceType == LOAD_BALANCER then validate self.args.node_port only IF available
        elif self.args.service_type == ServiceType.LOAD_BALANCER:
            if self.args.node_port is not None:
                if self.args.node_port < 30000 or self.args.node_port > 32767:
                    print_error(f"NodePort: {self.args.node_port} invalid")
                    print_error(f"Skipping this service")
                    return None
                else:
                    container_port.node_port = self.args.node_port
        # else validate self.args.node_port is NOT available
        elif self.args.node_port is not None:
            print_warning(
                f"NodePort: {self.args.node_port} provided without specifying ServiceType as NODE_PORT or LOAD_BALANCER"
            )
            print_warning("NodePort value will be ignored")
            self.args.node_port = None

        # Create the container
        k8s_container = CreateContainer(
            container_name=self.get_container_name(),
            app_name=app_name,
            image_name=self.args.image_name,
            image_tag=self.args.image_tag,
            # Equivalent to docker images CMD
            args=[self.args.command]
            if isinstance(self.args.command, str)
            else self.args.command,
            # Equivalent to docker images ENTRYPOINT
            command=self.args.entrypoint,
            image_pull_policy=self.args.image_pull_policy,
            envs_from_configmap=[container_env_cm.cm_name],
            envs_from_secret=[container_env_secret.secret_name]
            if container_env_secret
            else None,
            ports=[container_port],
            volumes=container_volumes,
            labels=k8s_build_context.labels,
        )

        # Create the deployment
        k8s_deployment = CreateDeployment(
            deploy_name=self.args.deploy_name or get_default_deploy_name(app_name),
            pod_name=self.args.pod_name or get_default_pod_name(app_name),
            app_name=app_name,
            namespace=k8s_build_context.namespace,
            service_account_name=k8s_build_context.service_account_name,
            replicas=self.args.replicas,
            containers=[k8s_container],
            pod_node_selector=pod_node_selector,
            restart_policy=self.args.restart_policy,
            termination_grace_period_seconds=self.args.termination_grace_period_seconds,
            volumes=container_volumes,
            labels=k8s_build_context.labels,
        )

        # Create the service
        k8s_service = CreateService(
            service_name=self.get_service_name(),
            app_name=app_name,
            namespace=k8s_build_context.namespace,
            service_account_name=k8s_build_context.service_account_name,
            service_type=self.args.service_type,
            deployment=k8s_deployment,
            ports=[container_port],
            labels=k8s_build_context.labels,
        )

        # Create the K8sResourceGroup
        k8s_resource_group = CreateK8sResourceGroup(
            name=app_name,
            enabled=self.args.enabled,
            config_maps=[container_env_cm],
            secrets=[container_env_secret] if container_env_secret else None,
            services=[k8s_service],
            deployments=[k8s_deployment],
        )

        return k8s_resource_group.create()

    def init_k8s_resource_groups(self, k8s_build_context: K8sBuildContext) -> None:
        k8s_rg = self.get_k8s_rg(k8s_build_context)
        if k8s_rg is not None:
            if self.k8s_resource_groups is None:
                self.k8s_resource_groups = OrderedDict()
            self.k8s_resource_groups[k8s_rg.name] = k8s_rg

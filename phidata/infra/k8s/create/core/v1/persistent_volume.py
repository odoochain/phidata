from typing import Optional, List, Dict
from typing_extensions import Literal

from pydantic import BaseModel

from phidata.infra.k8s.enums.api_version import ApiVersion
from phidata.infra.k8s.enums.kind import Kind
from phidata.infra.k8s.enums.pv import PVAccessMode
from phidata.infra.k8s.enums.volume_type import VolumeType
from phidata.infra.k8s.resource.core.v1.persistent_volume import (
    PersistentVolume,
    PersistentVolumeSpec,
    VolumeNodeAffinity,
    GcePersistentDiskVolumeSource,
    LocalVolumeSource,
    HostPathVolumeSource,
)
from phidata.infra.k8s.create.common.labels import create_component_labels_dict
from phidata.infra.k8s.resource.meta.v1.object_meta import ObjectMeta
from phidata.utils.cli_console import print_error, print_info
from phidata.utils.log import logger


class CreatePersistentVolume(BaseModel):
    pv_name: str
    app_name: str
    namespace: Optional[str] = None
    labels: Optional[Dict[str, str]] = None
    # AccessModes contains all ways the volume can be mounted.
    # More info: https://kubernetes.io/docs/concepts/storage/persistent-volumes#access-modes
    access_modes: List[PVAccessMode] = [PVAccessMode.READ_WRITE_ONCE]
    capacity: Optional[Dict[str, str]] = None
    # A list of mount options, e.g. ["ro", "soft"]. Not validated - mount will simply fail if one is invalid.
    # More info: https://kubernetes.io/docs/concepts/storage/persistent-volumes/#mount-options
    mount_options: Optional[List[str]] = None
    # NodeAffinity defines constraints that limit what nodes this volume can be accessed from.
    # This field influences the scheduling of pods that use this volume.
    node_affinity: Optional[VolumeNodeAffinity] = None
    # What happens to a persistent volume when released from its claim.
    #   The default policy is Retain.
    persistent_volume_reclaim_policy: Optional[
        Literal["Delete", "Recycle", "Retain"]
    ] = None
    # Name of StorageClass to which this persistent volume belongs.
    # Empty value means that this volume does not belong to any StorageClass.
    storage_class_name: Optional[str] = None
    volume_mode: Optional[str] = None

    ## Volume Type
    volume_type: VolumeType
    # Local represents directly-attached storage with node affinity
    local: Optional[LocalVolumeSource] = None
    # HostPath represents a directory on the host. Provisioned by a developer or tester.
    # This is useful for single-node development and testing only!
    # On-host storage is not supported in any way and WILL NOT WORK in a multi-node cluster.
    # More info: https://kubernetes.io/docs/concepts/storage/volumes#hostpath
    host_path: Optional[HostPathVolumeSource] = None
    # GCEPersistentDisk represents a GCE Disk resource that is attached to a
    # kubelet's host machine and then exposed to the pod. Provisioned by an admin.
    # More info: https://kubernetes.io/docs/concepts/storage/volumes#gcepersistentdisk
    gce_persistent_disk: Optional[GcePersistentDiskVolumeSource] = None

    def create(self) -> Optional[PersistentVolume]:
        """Creates the PersistentVolume resource"""

        pv_name = self.pv_name
        logger.debug(f"Init PersistentVolume resource: {pv_name}")

        pv_labels = create_component_labels_dict(
            component_name=pv_name,
            app_name=self.app_name,
            labels=self.labels,
        )
        persistent_volume = PersistentVolume(
            name=pv_name,
            api_version=ApiVersion.CORE_V1,
            kind=Kind.PERSISTENTVOLUME,
            metadata=ObjectMeta(
                name=pv_name,
                namespace=self.namespace,
                labels=pv_labels,
            ),
            spec=PersistentVolumeSpec(
                access_modes=self.access_modes,
                capacity=self.capacity,
                mount_options=self.mount_options,
                node_affinity=self.node_affinity,
                persistent_volume_reclaim_policy=self.persistent_volume_reclaim_policy,
                storage_class_name=self.storage_class_name,
                volume_mode=self.volume_mode,
            ),
        )

        if self.volume_type == VolumeType.LOCAL:
            if self.local is not None and isinstance(self.local, LocalVolumeSource):
                persistent_volume.spec.local = self.local
            else:
                print_error(
                    f"PersistentVolume {self.volume_type.value} selected but LocalVolumeSource not provided."
                )
        elif self.volume_type == VolumeType.HOST_PATH:
            if self.host_path is not None and isinstance(
                self.host_path, HostPathVolumeSource
            ):
                persistent_volume.spec.host_path = self.host_path
            else:
                print_error(
                    f"PersistentVolume {self.volume_type.value} selected but HostPathVolumeSource not provided."
                )
        elif self.volume_type == VolumeType.GCE_PERSISTENT_DISK:
            if self.gce_persistent_disk is not None and isinstance(
                self.gce_persistent_disk, GcePersistentDiskVolumeSource
            ):
                persistent_volume.spec.gce_persistent_disk = self.gce_persistent_disk
            else:
                print_error(
                    f"PersistentVolume {self.volume_type.value} selected but GcePersistentDiskVolumeSource not provided."
                )

        return persistent_volume

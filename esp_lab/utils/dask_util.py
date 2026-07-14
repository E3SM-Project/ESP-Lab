from dataclasses import dataclass
from typing import Optional, Tuple
import dask
from dask.distributed import Client

@dataclass
class DaskConfig:
    cluster_type: str = "local"   # local, slurm, casper_pbs, none
    workers: int = 4
    cores: int = 4
    memory: str = "16GB"
    walltime: str = "02:00:00"
    queue: Optional[str] = None
    project: Optional[str] = None
    interface: Optional[str] = None


def get_cluster_client(cfg: DaskConfig) -> Tuple[object | None, object | None]:
    """
    Create a Dask cluster + client based on config.
    """

    dask.config.set({'array.slicing.split_large_chunks': True})

    if cfg.cluster_type in (None, "none"):
        return None, None

    # -----------------------
    # Local (laptop / debug)
    # -----------------------
    if cfg.cluster_type == "local":
        from dask.distributed import LocalCluster

        cluster = LocalCluster(
            n_workers=cfg.workers,
            threads_per_worker=1,
        )
        client = Client(cluster)
        return cluster, client

    # -----------------------
    # SLURM (Perlmutter)
    # -----------------------
    if cfg.cluster_type == "slurm":
        from dask_jobqueue import SLURMCluster

        cluster = SLURMCluster(
            cores=cfg.cores,
            processes=1,
            memory=cfg.memory,
            walltime=cfg.walltime,
            queue=cfg.queue,      # e.g., "regular", "debug"
            account=cfg.project,  # e3sm
        )
        cluster.scale(cfg.workers)

        client = Client(cluster)
        return cluster, client

    # -----------------------
    # Casper (NCAR)
    # -----------------------
    if cfg.cluster_type == "casper_pbs":
        from dask_jobqueue import PBSCluster

        cluster = PBSCluster(
            cores=1,
            memory="20GB",
            processes=1,
            queue="casper",
            resource_spec="select=1:ncpus=1:mem=20GB",
            project=cfg.project or "NCGD0011",
            walltime=cfg.walltime,
            interface=cfg.interface or "ib0",
        )
        cluster.scale(cfg.workers)

        client = Client(cluster)
        return cluster, client

    raise ValueError(f"Unknown cluster_type: {cfg.cluster_type}")


def close_cluster(cluster=None, client=None):
    """Safely close Dask resources."""
    try:
        if client is not None:
            client.close()
    except Exception:
        pass

    try:
        if cluster is not None:
            cluster.close()
    except Exception:
        pass


# -----------------------
# Optional helpers
# -----------------------

def maybe_persist(obj, do_persist=True):
    return obj.persist() if do_persist else obj


def maybe_load(obj, do_load=True):
    return obj.load() if do_load else obj

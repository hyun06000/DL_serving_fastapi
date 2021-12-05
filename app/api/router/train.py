import os
import re
import subprocess
import multiprocessing

from fastapi import APIRouter

from app.utils import (
    NniWatcher,
    get_free_port,
    write_yaml,
)
from logger import L

router = APIRouter(
    prefix="/train",
    #tags=["train"],
    responses={404: {"description": "Not Found"}},
)

@router.get("/")
def check_point():
    return {"description": "train"}

@router.put("/insurance")
def train_insurance(
    experiment_name:str="exp1",
    experimenter:str="User",
    model_name:str="insurance_fee_model",
    version:float=0.1
):
    """
    insurance와 관련된 학습을 실행하기 위한 API입니다.\n
    \n
    Args:\n
        experiment_name (str): 실험이름. 기본 값: exp1 \n
        experimenter (str): 실험자의 이름. 기본 값: DongUk \n
        model_name (str): 모델의 이름. 기본 값: insurance_fee_model \n
        version (float): 실험의 버전. 기본 값: 0.1 \n
    \n
    Returns: \n
        msg: 실험 실행의 성공과 상관없이 포트번호를 포함한 NNI Dashboard의 주소를 반환합니다. \n
    \n
    Note:\n
        실험의 최종 결과를 반환하지 않습니다.\n
    """
    PORT = get_free_port()
    L.info(
        f"Train Args info\n\tport: {PORT}\n\texperiment_name: {experiment_name}\n\texperimenter: {experimenter}\n\tmodel_name: {model_name}\n\tversion: {version}"
    )
    root = "./"
    path = "experiments/insurance"
    os.makedirs(path, exist_ok=True)
    try:
        write_yaml(
            path, experiment_name, experimenter, model_name, version
        )
        nni_create_result = subprocess.getoutput(
            "nnictl create --port {} --config {}/{}.yaml".format(
                PORT, root+path, model_name
            )
        )
        sucs_msg = "Successfully started experiment!"

        if sucs_msg in nni_create_result:
            p = re.compile(r"The experiment id is ([a-zA-Z0-9]+)\n")
            expr_id = p.findall(nni_create_result)[0]
            nni_watcher = NniWatcher(
                expr_id, experiment_name, experimenter, version
            )
            m_process = multiprocessing.Process(target=nni_watcher.execute)
            m_process.start()

            L.info(nni_create_result)
            return {"msg": nni_create_result, "error": None}
        else:
            return {"msg": "nni_error", "error": nni_create_result}

    except Exception as e:
        L.error(e)
        return {"msg": "Can't start experiment", "error": str(e)}
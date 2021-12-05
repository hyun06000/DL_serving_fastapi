import time
import subprocess
import socketserver

import pickle
import codecs
import yaml

from app.database import engine
from app.query import (
    UPDATE_TEMP_MODEL_DATA,
    SELECT_TEMP_MODEL_BY_EXPR_NAME,
    SELECT_MODEL_METADATA_BY_EXPR_NAME,
    INSERT_MODEL_CORE,
    INSERT_MODEL_METADATA,
    UPDATE_MODEL_CORE,
    UPDATE_MODEL_METADATA,
    DELETE_ALL_EXPERIMENTS_BY_EXPR_NAME,
    INSERT_OR_UPDATE_MODEL,
    INSERT_OR_UPDATE_SCORE
)
from logger import L




def get_free_port():
    """
    호출 즉시 사용가능한 포트번호를 반환합니다.
    Returns:
        현재 사용가능한 포트번호
    Examples:
        >>> avail_port = get_free_port() # 사용 가능한 포트, 그때그때 다름
        >>> print(avail_port)
        45675
    """
    with socketserver.TCPServer(("localhost", 0), None) as s:
        free_port = s.server_address[1]
    return free_port


def write_yaml(path, experiment_name, experimenter, model_name, version):
    """
    NNI 실험을 시작하기 위한 config.yml파일을 작성하는 함수 입니다.
    Args:
        path(str): 실험의 경로
        experiment_name(str): 실험의 이름
        experimenter(str): 실험자의 이름
        model_name(str): 모델의 이름
        version(float): 버전
    Returns:
        반환 값은 없으며 입력받은 경로로 yml파일이 작성됩니다.
    """
    with open("{}/{}.yaml".format(path, model_name), "w") as yml_config_file:
        yaml.dump(
            {
                "authorName": f"{experimenter}",
                "experimentName": f"{experiment_name}",
                "trialConcurrency": 1,
                "maxExecDuration": "1h",
                "maxTrialNum": 10,
                "trainingServicePlatform": "local",
                "searchSpacePath": "search_space.json",
                "useAnnotation": False,
                "tuner": {
                    "builtinTunerName": "Anneal",
                    "classArgs": {"optimize_mode": "minimize"},
                },
                "trial": {
                    "command": "python trial.py -e {} -n {} -m {} -v {}".format(
                        experimenter, experiment_name, model_name, version
                    ),
                    "codeDir": ".",
                },
            },
            yml_config_file,
            default_flow_style=False,
        )

        yml_config_file.close()

    return

class NniWatcher:
    """
    experiment_id를 입력받아 해당 id를 가진 nni 실험을 모니터링하고 모델 파일을 관리해주는 클래스입니다.
    생성되는 scikit learn 모델을 DB의 임시 테이블에 저장하여 주기적으로 업데이트 합니다.
    이후 실험의 모든 프로세스가 종료되면 가장 성능이 좋은 모델과 점수를 업데이트 합니다.
    
    Attributes:
        experiment_id(str): nni experiment를 실행할 때 생성되는 id
        experiment_name(str): 실험의 이름
        experimenter(str): 실험자의 이름
        version(str): 실험의 버전
        minute(int): 감시 주기
        is_kill(bool, default=True): 실험 감시하며 실험이 끝나면 종료할지 결정하는 변수
        top_cnt(int, default=3): 임시로 최대 몇개의 실험을 저장할지 결정하는 변수
        evaluation_criteria(str, default="val_mae"): 어떤 평가기준으로 모델을 업데이트 할지 결정하는 변수
    
    Examples:
        >>> watcher = NniWatcher(expr_id, experiment_name, experimenter, version)
        >>> watcher.execute()
    
    """

    def __init__(
        self,
        experiment_id,
        experiment_name,
        experimenter,
        version,
        minute=1,
        is_kill=True,
        top_cnt=3,
        evaluation_criteria="val_mae",
    ):
        self.experiment_id = experiment_id
        self.experiment_name = experiment_name
        self.experimenter = experimenter
        self.version = version
        self.is_kill = is_kill
        self.top_cnt = top_cnt
        self.evaluation_criteria = evaluation_criteria
        self._wait_minute = minute * 20
        self._experiment_list = None
        self._running_experiment = None

    def execute(self):
        """
        모든 함수를 실행합니다.
        """
        self.watch_process()
        self.model_final_update()
    
    def watch_process(self):
        """
        사용자가 지정한 시간을 주기로 실험 프로세스가 진행 중인지 감시하고 "DONE"상태로 변경되면 실험을 종료합니다.
        모델의 score를 DB에 주기적으로 업데이트 해줍니다.
        """
        if self.is_kill:
            while True:
                self.get_running_experiment()
                if self._running_experiment and (
                    "DONE" in self._running_experiment[0]
                ):
                    _stop_expr = subprocess.getoutput(
                        "nnictl stop {}".format(self.experiment_id)
                    )
                    L.info(_stop_expr)
                    break

                elif self.experiment_id not in self._experiment_list:
                    L.error("Experiment ID not in Current Experiment List")
                    L.info(self._experiment_list)
                    break

                else:
                    self.model_keep_update()
                time.sleep(self._wait_minute)
    
    def get_running_experiment(self):
        """
        실행중인 실험의 목록을 가져와 저장합니다.
        """
        self._experiment_list = subprocess.getoutput("nnictl experiment list")
        self._running_experiment = [
            expr
            for expr in self._experiment_list.split("\n")
            if self.experiment_id in expr
        ]
        L.info(self._running_experiment)
    
    def model_keep_update(self):
        """
        scikit learn 모델의 성능을 DB에 업데이트 합니다.
        """
        engine.execute(
            UPDATE_TEMP_MODEL_DATA.format(
                self.experiment_name, self.evaluation_criteria, self.top_cnt
            )
        )
    def model_final_update(self):
        """
        실험 종료시 실행되는 함수로 모델의 최종 점수와 모델 파일을 DB에 업데이트 해줍니다.
        """
        final_result = engine.execute(
            SELECT_TEMP_MODEL_BY_EXPR_NAME.format(
                self.experiment_name, self.evaluation_criteria
            )
        ).fetchone()

        saved_result = engine.execute(
            SELECT_MODEL_METADATA_BY_EXPR_NAME.format(self.experiment_name)
        ).fetchone()

        a = pickle.loads(codecs.decode(final_result.model_file, "base64"))
        pickled_model = codecs.encode(pickle.dumps(a), "base64").decode()

        if saved_result is None:
            engine.execute(
                INSERT_MODEL_CORE.format(
                    final_result.model_name, pickled_model
                )
            )
            engine.execute(
                INSERT_MODEL_METADATA.format(
                    self.experiment_name,
                    final_result.model_name,
                    self.experimenter,
                    self.version,
                    final_result.train_mae,
                    final_result.val_mae,
                    final_result.train_mse,
                    final_result.val_mse,
                )
            )
        elif (
            saved_result[self.evaluation_criteria]
            > final_result[self.evaluation_criteria]
        ):
            engine.execute(
                UPDATE_MODEL_CORE.format(
                    pickled_model, saved_result.model_name
                )
            )
            engine.execute(
                UPDATE_MODEL_METADATA.format(
                    final_result.train_mae,
                    final_result.val_mae,
                    final_result.train_mse,
                    final_result.val_mse,
                    self.experiment_name,
                )
            )

        engine.execute(
            DELETE_ALL_EXPERIMENTS_BY_EXPR_NAME.format(self.experiment_name)
        )

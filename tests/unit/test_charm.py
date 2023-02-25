# Copyright 2022 Guillaume Belanger
# See LICENSE file for licensing details.

import unittest
from unittest.mock import Mock, patch

from ops import testing
from ops.model import ActiveStatus

from charm import UDROperatorCharm


class TestCharm(unittest.TestCase):
    @patch(
        "charm.KubernetesServicePatch",
        lambda charm, ports: None,
    )
    def setUp(self):
        self.namespace = "whatever"
        self.harness = testing.Harness(UDROperatorCharm)
        self.harness.set_model_name(name=self.namespace)
        self.addCleanup(self.harness.cleanup)
        self.harness.begin()

    def _nrf_is_available(self) -> str:
        nrf_url = "http://1.1.1.1"
        nrf_relation_id = self.harness.add_relation("nrf", "nrf-operator")
        self.harness.add_relation_unit(
            relation_id=nrf_relation_id, remote_unit_name="nrf-operator/0"
        )
        self.harness.update_relation_data(
            relation_id=nrf_relation_id, app_or_unit="nrf-operator", key_values={"url": nrf_url}
        )
        return nrf_url

    @patch("ops.model.Container.push")
    def test_given_can_connect_to_worload_when_nrf_is_available_then_config_file_is_written(
        self,
        patch_push,
    ):
        nrf_url = "2.2.2.2"
        udr_hostname = f"udr-operator.{self.namespace}.svc.cluster.local"
        self.harness.set_can_connect(container="udr", val=True)

        self.harness.charm._on_nrf_available(event=Mock(url=nrf_url))

        patch_push.assert_called_with(
            path="/etc/udr/udrcfg.conf",
            source=f'configuration:\n  mongodb:\n    name: free5gc\n    url: mongodb://mongodb-arbiter-headless\n  nrfUri: { nrf_url }\n  plmnSupportList:\n  - plmnId:\n      mcc: "208"\n      mnc: "93"\n  - plmnId:\n      mcc: "333"\n      mnc: "88"\n  sbi:\n    bindingIPv4: 0.0.0.0\n    port: 29504\n    registerIPv4: { udr_hostname }\n    scheme: http\ninfo:\n  description: UDR initial local configuration\n  version: 1.0.0\nlogger:\n  AMF:\n    ReportCaller: false\n    debugLevel: info\n  AUSF:\n    ReportCaller: false\n    debugLevel: info\n  Aper:\n    ReportCaller: false\n    debugLevel: info\n  CommonConsumerTest:\n    ReportCaller: false\n    debugLevel: info\n  FSM:\n    ReportCaller: false\n    debugLevel: info\n  MongoDBLibrary:\n    ReportCaller: false\n    debugLevel: info\n  N3IWF:\n    ReportCaller: false\n    debugLevel: info\n  NAS:\n    ReportCaller: false\n    debugLevel: info\n  NGAP:\n    ReportCaller: false\n    debugLevel: info\n  NRF:\n    ReportCaller: false\n    debugLevel: info\n  NamfComm:\n    ReportCaller: false\n    debugLevel: info\n  NamfEventExposure:\n    ReportCaller: false\n    debugLevel: info\n  NsmfPDUSession:\n    ReportCaller: false\n    debugLevel: info\n  NudrDataRepository:\n    ReportCaller: false\n    debugLevel: info\n  OpenApi:\n    ReportCaller: false\n    debugLevel: info\n  PCF:\n    ReportCaller: false\n    debugLevel: info\n  PFCP:\n    ReportCaller: false\n    debugLevel: info\n  PathUtil:\n    ReportCaller: false\n    debugLevel: info\n  SMF:\n    ReportCaller: false\n    debugLevel: info\n  UDM:\n    ReportCaller: false\n    debugLevel: info\n  UDR:\n    ReportCaller: false\n    debugLevel: info\n  WEBUI:\n    ReportCaller: false\n    debugLevel: info',  # noqa: E501
        )

    @patch("charm.check_output")
    @patch("ops.model.Container.exists")
    def test_given_config_file_is_written_when_pebble_ready_then_pebble_plan_is_applied(
        self,
        patch_exists,
        patch_check_output,
    ):
        pod_ip = "1.1.1.1"
        patch_exists.return_value = True
        patch_check_output.return_value = pod_ip.encode()

        self._nrf_is_available()

        self.harness.container_pebble_ready(container_name="udr")

        expected_plan = {
            "services": {
                "udr": {
                    "override": "replace",
                    "command": "./udr --udrcfg /etc/udr/udrcfg.conf",
                    "startup": "enabled",
                    "environment": {
                        "GRPC_GO_LOG_VERBOSITY_LEVEL": "99",
                        "GRPC_GO_LOG_SEVERITY_LEVEL": "info",
                        "GRPC_TRACE": "all",
                        "GRPC_VERBOSITY": "debug",
                        "POD_IP": pod_ip,
                        "MANAGED_BY_CONFIG_POD": "true",
                    },
                }
            },
        }

        updated_plan = self.harness.get_container_pebble_plan("udr").to_dict()

        self.assertEqual(expected_plan, updated_plan)

    @patch("charm.check_output")
    @patch("ops.model.Container.exists")
    def test_given_config_file_is_written_when_pebble_ready_then_status_is_active(
        self, patch_exists, patch_check_output
    ):
        patch_exists.return_value = True
        patch_check_output.return_value = b"1.2.3.4"

        self._nrf_is_available()

        self.harness.container_pebble_ready("udr")

        self.assertEqual(self.harness.model.unit.status, ActiveStatus())

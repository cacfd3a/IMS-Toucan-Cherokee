{ config, lib, pkgs, ... }:

let
  cfg = config.services.cherokeeToucan;
  image = "ims-toucan-cherokee:2022.07.18.01";
  source = builtins.path {
    name = "ims-toucan-cherokee-source";
    path = ../.;
    filter = path: type:
      let name = builtins.baseNameOf path;
      in !(builtins.elem name [ ".git" "Models" "test-files" "venv" "__pycache__" ".pytest_cache" ]);
  };
in
{
  options.services.cherokeeToucan = {
    enable = lib.mkEnableOption "IMS-Toucan Cherokee text-to-speech service";

    bindAddress = lib.mkOption {
      type = lib.types.str;
      default = "127.0.0.1";
      description = "Host address to bind the HTTP service to.";
    };

    port = lib.mkOption {
      type = lib.types.port;
      default = 8765;
      description = "Host port for the HTTP service.";
    };

    dataDir = lib.mkOption {
      type = lib.types.str;
      default = "/var/lib/cherokee-toucan";
      description = "Persistent directory for downloaded model checkpoints.";
    };
  };

  config = lib.mkIf cfg.enable {
    virtualisation.podman.enable = lib.mkDefault true;

    systemd.tmpfiles.rules = [ "d ${cfg.dataDir}/Models 0750 root root -" ];

    systemd.services.cherokee-toucan = {
      description = "IMS-Toucan Cherokee text-to-speech service";
      wantedBy = [ "multi-user.target" ];
      after = [ "network-online.target" ];
      wants = [ "network-online.target" ];
      requiresMountsFor = [ cfg.dataDir ];
      serviceConfig = {
        Type = "simple";
        ExecStartPre = "${pkgs.podman}/bin/podman build --tag ${image} --file ${source}/Dockerfile ${source}";
        ExecStart = ''
          ${pkgs.podman}/bin/podman run --rm --name ims-toucan-cherokee \
            --publish ${cfg.bindAddress}:${toString cfg.port}:8765 \
            --volume ${cfg.dataDir}/Models:/opt/IMS-Toucan/Models:Z \
            ${image}
        '';
        ExecStop = "${pkgs.podman}/bin/podman stop --time 10 ims-toucan-cherokee";
        Restart = "always";
        RestartSec = 5;
        TimeoutStartSec = 0;
        TimeoutStopSec = 20;
      };
    };
  };
}
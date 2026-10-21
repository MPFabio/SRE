# Installer SRE dans EKS

## Préparation

- Se connecter sur utils-stagiaireXX
- Installer helm

```console
[stagiairexx@utils-stagiairexx ~]$ curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100 12252 100 12252   0     0 310067     0  --:--:-- --:--:-- --:--:-- 322421
Downloading https://get.helm.sh/helm-v3.22.1-linux-amd64.tar.gz
Verifying checksum... Done.
Preparing to install helm into /usr/local/bin

We trust you have received the usual lecture from the local System
Administrator. It usually boils down to these three things:

    #1) Respect the privacy of others.
    #2) Think before you type.
    #3) With great power comes great responsibility.

For security reasons, the password you type will not be visible.

[sudo] password for stagiairexx: 

Preparing to install helm into /usr/local/bin
helm installed into /usr/local/bin/helm

```

- Récupérer le répertoire Git du projet SRE

```console
[stagiaire04@utils-stagiaire04 Projets]$ git config --global credential.helper store
[stagiaire04@utils-stagiaire04 Projets]$ git clone https://github.com/MPFabio/SRE.git
Cloning into 'SRE'...
Username for 'https://github.com': javond-cap
Password for 'https://javond-cap@github.com':
remote: Enumerating objects: 120, done.
remote: Counting objects: 100% (120/120), done.
remote: Compressing objects: 100% (93/93), done.
remote: Total 120 (delta 11), reused 120 (delta 11), pack-reused 0 (from 0)
Receiving objects: 100% (120/120), 110.20 KiB | 5.80 MiB/s, done.
Resolving deltas: 100% (11/11), done.
[stagiaire04@utils-stagiaire04 Projets]$ git
git                 git-receive-pack    git-shell           git-upload-archive  git-upload-pack
```

- Installez docker

```console
sudo dnf install docker
sudo systemctl enable docker.service
sudo systemctl start docker.service
sudo usermod -aG docker stagiaire04
docker version
    Client:
     Version:           25.0.14
     API version:       1.44
     Go version:        go1.25.12 X:nodwarf5
     Git commit:        0bab007
     Built:             Tue Jul 28 00:00:00 2026
     OS/Arch:           linux/amd64
     Context:           default

    Server:
     Engine:
      Version:          25.0.16
      API version:      1.44 (minimum version 1.24)
      Go version:       go1.25.12 X:nodwarf5
      Git commit:       6fdf0a6
      Built:            Tue Jul 28 00:00:00 2026
      OS/Arch:          linux/amd64
      Experimental:     false
     containerd:
      Version:          2.2.5+unknown
      GitCommit:
     runc:
      Version:          1.3.5
      GitCommit:        488fc13e1f2d3d73ec36d829fdf2c98e47dc5ae8
     docker-init:
      Version:          0.19.0
      GitCommit:        de40ad0
```

- connecter docker au nexus local

```console
[stagiaire04@utils-stagiaire04 ~]$ docker login docker-push.reskilling.internal
Username: stagiaire04
Password:
WARNING! Your password will be stored unencrypted in /home/stagiaire04/.docker/config.json.
Configure a credential helper to remove this warning. See
https://docs.docker.com/engine/reference/commandline/login/#credentials-store

Login Succeeded
```

- construire les images

```console
export REGISTRY=docker-push.reskilling.internal/stagiaire04

for SVC in api-gateway catalog-service cart-service orders-service payment-service users-service
do

    docker build --tag $REGISTRY/$SVC:lab --file microservices/$SVC/Dockerfile microservices/

done

docker build --tag $REGISTRY/lab-controller:lab lab-controller/api/
docker build --tag $REGISTRY/traffic-generator:lab traffic-generator/
```

- Pousser les images

```console
for SVC in api-gateway catalog-service cart-service orders-service payment-service users-service lab-controller traffic-generator
do

    docker push $REGISTRY/$SVC:lab

done
```


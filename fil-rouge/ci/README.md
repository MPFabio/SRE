# Pipeline de construction d'image

Ce pipeline construit l'image de votre module et la pousse sur le registry
du GitLab commun, dans votre projet, à chaque push sur la branche par
défaut. Il remplace le `docker build` et le `docker push` faits à la main
sur `utils-stagiaireXX`.

## Mise en place

Votre projet GitLab contient votre module, avec son `Dockerfile` à la
racine.

1. Copiez [`.gitlab-ci.yml`](.gitlab-ci.yml) à la racine de votre projet, ou
   ajoutez son job `build-image` à votre pipeline existant.
2. Poussez le commit, puis suivez le job dans **Build** → **Pipelines**.
3. Une fois le job vert, **Deploy** → **Container Registry** affiche deux
   tags : le hash court du commit et `latest`.

Si votre `Dockerfile` n'est pas à la racine, remplacez le `.` final de la
commande `docker build` par le chemin du dossier.

## Ce que fait le job

| Ligne | Rôle |
|---|---|
| `image` et `services` | Un client Docker et son démon (`docker:dind`), téléchargés depuis Nexus |
| `rules` | Ne construit que sur la branche par défaut |
| `docker login` | Se connecte au registry avec les identifiants fournis par GitLab au job |
| `docker build` | Construit l'image, étiquetée avec le hash du commit et `latest` |
| `docker push` | Publie les deux tags |

Les variables `CI_REGISTRY`, `CI_REGISTRY_IMAGE`, `CI_REGISTRY_USER`,
`CI_REGISTRY_PASSWORD` et `CI_COMMIT_SHORT_SHA` sont fournies par GitLab :
rien à configurer, ni mot de passe à écrire dans le pipeline.

## Déployer l'image construite

Le tag du commit s'affiche dans le registry et dans le log du job :

```bash
helm upgrade lab helm/reskilling-lab --namespace $STAGIAIRE --reuse-values \
    --set learnerService.image=$IMAGE:<tag du commit>
```

`$IMAGE` est le chemin de votre image (voir [Déployer votre module](../README.md#déployer-votre-module)).
Le secret de lecture `gitlab-registry` créé pour le déploiement manuel
reste valable.

<details>
<summary>Ça bloque ?</summary>

| Symptôme | Cause probable | Solution |
|---|---|---|
| `denied: access forbidden` au push | Registry désactivé pour le projet | **Settings** → **General** → **Visibility** : activer **Container registry** |
| Le job ne se lance pas après un push | Push sur une autre branche que la branche par défaut | Normal, voir `rules` ; ou supprimer le bloc `rules` |
| `ImagePullBackOff` après le `helm upgrade` | Tag mal recopié, ou secret de lecture absent | `kubectl describe pod -l app=<nom>`, vérifier le tag et le secret `gitlab-registry` |

</details>

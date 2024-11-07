# dev
d:
	yarn
	yarn start

# push
p:
	git push

# append to previous pr
a:
	git add .
	git ca --no-edit
	git push -f

# commit current files with push
c:
	git add .
	git cz
	$(MAKE) p

cf:
	git add .
	git cz --no-edit
	$(MAKE) p

# commit current files
cz:
	git add .
	git cz

# commit current files without verify
cw:
	git add .
	git cz --no-verify

# commit current files without verify and push
aw:
	git add .
	git ca --no-edit --no-verify
	git push -f

# switch
s:
	git fetch
	git co $(b)
	$(MAKE) d

# switch rc
rc:
	git co rc
	git p
	$(MAKE) d

# switch new branch from rc
sn:
	git co rc
	git pull
	git co -b $(b)
	$(MAKE) d

# solve rc conflict
sr:
	git fetch
	git merge origin/rc

# upgrade
u:
ifndef pkg
	@echo "请指定要升级的包名，例如: make u pkg=react"
	@exit 1
endif
	@echo "正在升级 $(pkg) 到最新版本..."
	nu $(pkg)@latest

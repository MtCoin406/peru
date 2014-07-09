#! /usr/bin/env python3

import configparser
import os

from peru import plugin_shared

import git_plugin_shared
from git_plugin_shared import git


class FetchJob:
    def __init__(self, cache_path, dest, url, rev):
        self.cache_path = cache_path
        self.dest = dest
        self.url = url
        self.rev = rev

        self.fetch()

    def log(self, command):
        print('git {} {}'.format(command, self.url))

    def clone_cached(self, url):
        return git_plugin_shared.clone_if_needed(
            url,
            self.cache_path,
            lambda: self.log('clone'))

    def already_has_rev(self, repo, rev):
        try:
            # Make sure the rev exists.
            git('cat-file', '-e', rev, git_dir=repo)
            # Get the hash for the rev.
            output = git('rev-parse', rev, git_dir=repo)
        except:
            return False

        # Only return True for revs that are absolute hashes.
        # We could consider treating tags the way, but...
        # 1) Tags actually can change.
        # 2) It's not clear at a glance if something is a branch or a hash.
        # Keep it simple.
        return output.strip() == rev

    def checkout_tree(self, clone, rev, dest):
        self.log('checkout')
        git('--work-tree=' + dest, 'checkout', rev, '--', '.', git_dir=clone)
        self.checkout_subrepos(clone, rev, dest)

    def checkout_subrepos(self, clone_path, rev, work_tree):
        gitmodules = os.path.join(work_tree, '.gitmodules')
        if not os.path.exists(gitmodules):
            return

        parser = configparser.ConfigParser()
        parser.read(gitmodules)
        for section in parser.sections():
            sub_relative_path = parser[section]['path']
            sub_full_path = os.path.join(work_tree, sub_relative_path)
            sub_url = parser[section]['url']
            sub_clone = self.clone_cached(sub_url)
            ls_tree = git('ls-tree', '-r', rev, sub_relative_path,
                          git_dir=clone_path)
            sub_rev = ls_tree.split()[2]
            self.checkout_tree(sub_clone, sub_rev, sub_full_path)

    def fetch(self):
        cached_dir = self.clone_cached(self.url)
        if not self.already_has_rev(cached_dir, self.rev):
            self.log('fetch')
            git('fetch', '--prune', git_dir=cached_dir)

        self.checkout_tree(cached_dir, self.rev, self.dest)


fields, dest, cache_path = plugin_shared.parse_plugin_args(
    git_plugin_shared.required_fields,
    git_plugin_shared.optional_fields)
url, rev, _ = git_plugin_shared.unpack_fields(fields)

FetchJob(cache_path, dest, url, rev)

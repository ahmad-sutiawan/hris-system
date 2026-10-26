import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';
import 'api_exception.dart';

class PagedListState {
  const PagedListState({
    this.items = const [],
    this.nextPage,
    this.loadingMore = false,
    this.loadMoreError,
  });

  final List<dynamic> items;
  final int? nextPage;
  final bool loadingMore;
  final String? loadMoreError;

  bool get hasMore => nextPage != null;

  PagedListState copyWith({
    List<dynamic>? items,
    int? nextPage,
    bool clearNext = false,
    bool? loadingMore,
    String? loadMoreError,
    bool clearLoadMoreError = false,
  }) {
    return PagedListState(
      items: items ?? this.items,
      nextPage: clearNext ? null : (nextPage ?? this.nextPage),
      loadingMore: loadingMore ?? this.loadingMore,
      loadMoreError: clearLoadMoreError ? null : (loadMoreError ?? this.loadMoreError),
    );
  }
}

class PagedListNotifier extends StateNotifier<AsyncValue<PagedListState>> {
  PagedListNotifier(
    this._api, {
    required this.path,
    this.query,
    this.pageSize = 50,
  }) : super(const AsyncLoading()) {
    refresh();
  }

  final ApiClient _api;
  final String path;
  final Map<String, dynamic>? query;
  final int pageSize;
  int _generation = 0;
  bool _loadingMore = false;

  Future<void> refresh() async {
    final generation = ++_generation;
    _loadingMore = false;
    state = const AsyncLoading();
    try {
      final page = await _api.getPage(path, query: query, pageSize: pageSize);
      if (generation != _generation) return;
      state = AsyncData(PagedListState(items: page.items, nextPage: page.nextPage));
    } catch (error, stackTrace) {
      if (generation != _generation) return;
      state = AsyncError(error, stackTrace);
    }
  }

  Future<void> loadMore() async {
    final current = state.asData?.value;
    final next = current?.nextPage;
    if (current == null || next == null || _loadingMore) return;
    final generation = _generation;
    _loadingMore = true;
    state = AsyncData(current.copyWith(loadingMore: true, clearLoadMoreError: true));
    try {
      final page = await _api.getPage(
        path,
        query: query,
        page: next,
        pageSize: pageSize,
      );
      if (generation != _generation) return;
      state = AsyncData(
        PagedListState(
          items: [...current.items, ...page.items],
          nextPage: page.nextPage,
        ),
      );
    } catch (error) {
      if (generation != _generation) return;
      state = AsyncData(
        current.copyWith(loadingMore: false, loadMoreError: friendlyError(error)),
      );
    } finally {
      if (generation == _generation) _loadingMore = false;
    }
  }
}

bool onPagedScroll(ScrollNotification notification, VoidCallback loadMore) {
  final metrics = notification.metrics;
  if (metrics.maxScrollExtent <= 0) return false;
  if (metrics.pixels >= metrics.maxScrollExtent - 320) {
    loadMore();
  }
  return false;
}

class PagedListFooter extends StatelessWidget {
  const PagedListFooter({super.key, required this.page});

  final PagedListState page;

  @override
  Widget build(BuildContext context) {
    if (page.loadingMore) {
      return const Padding(
        padding: EdgeInsets.fromLTRB(16, 8, 16, 28),
        child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
      );
    }
    final error = page.loadMoreError;
    if (error != null) {
      return Padding(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 28),
        child: Text(error, textAlign: TextAlign.center),
      );
    }
    return const SizedBox(height: 24);
  }
}
